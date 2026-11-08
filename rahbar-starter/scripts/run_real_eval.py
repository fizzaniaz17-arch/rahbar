"""Run three real-corpus evaluations on the dedicated RAHBAR Minikube profile."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "rahbar-real-eval"
KUBE = ["kubectl", "--context", PROFILE, "-n", "rahbar"]
TRIALS = ((250, 25), (400, 50), (600, 75))
IMAGE_TAG = "real-eval"
MODEL_IMAGE = "ollama/ollama:0.9.6"
OUTPUT = ROOT / "eval" / "real-eval-runs"


def run(*command, check=True, **options):
    print("+", *command, flush=True)
    return subprocess.run(command, cwd=ROOT, check=check, **options)


def kube(*args, **options):
    return run(*KUBE, *args, **options)


def apply(*resources):
    kube("apply", "-f", "-", input=yaml.safe_dump_all(resources).encode("utf-8"))


def corpus_files():
    raw = ROOT / "corpus" / "raw"
    index = raw / "_index.json"
    entries = json.loads(index.read_text(encoding="utf-8"))
    manifest = (ROOT / "corpus" / "MANIFEST.md").read_text(encoding="utf-8")
    hashes = dict(re.findall(r"\| `([^`]+)` \| [\d,]+ \| `([0-9a-f]{64})` \|", manifest))
    names = [entry["file"] for entry in entries]
    if len(names) != 6 or set(names) != hashes.keys():
        raise ValueError("Expected the same six files in _index.json and MANIFEST.md")
    for entry in entries:
        file = raw / entry["file"]
        if file.parent != raw or not file.is_file():
            raise ValueError(f"Invalid corpus file: {file}")
        checksum = hashlib.sha256(file.read_bytes()).hexdigest()
        if checksum != hashes[file.name] or checksum != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {file.name}")
    return [index, *(raw / name for name in names)]


def prepare_stack(files):
    rendered = kube("kustomize", "k8s/overlays/prod", capture_output=True).stdout
    resources = list(yaml.safe_load_all(rendered))
    job, = [item for item in resources if item["kind"] == "Job"]
    resources.remove(job)
    for item in resources:
        kind = item["kind"]
        if kind == "ConfigMap" and item["metadata"]["name"] == "rahbar-config":
            item["data"].update(LLM_MODEL="llama3.2:3b", TEMPERATURE="0")
        if kind == "CronJob":
            item["spec"]["suspend"] = True
    for item in (job, *resources):
        if item["kind"] in {"Deployment", "Job", "CronJob"}:
            spec = item["spec"]
            if item["kind"] == "CronJob":
                spec = spec["jobTemplate"]["spec"]
            for container in spec["template"]["spec"]["containers"]:
                image = container["image"]
                if image.startswith("rahbar-") and image.endswith(":dev"):
                    container["image"] = image.removesuffix(":dev") + ":" + IMAGE_TAG

    namespace, = [item for item in resources if item["kind"] == "Namespace"]
    apply(namespace, *[item for item in resources if item is not namespace])

    ollama = {"app": "ollama"}
    apply(
        {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "ollama"},
         "spec": {"selector": {"matchLabels": ollama},
                  "template": {"metadata": {"labels": ollama}, "spec": {
                      "automountServiceAccountToken": False,
                      "containers": [{"name": "ollama", "image": MODEL_IMAGE,
                                      "ports": [{"containerPort": 11434}],
                                      "readinessProbe": {"tcpSocket": {"port": 11434}}}],
                  }}}},
        {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "ollama"},
         "spec": {"selector": ollama, "ports": [{"port": 11434}]}},
        {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
         "metadata": {"name": "ollama-model-download"},
         "spec": {"podSelector": {"matchLabels": ollama}, "policyTypes": ["Egress"],
                  "egress": [{"ports": [{"protocol": "TCP", "port": 443}]}]}},
    )
    try:
        kube("rollout", "status", "deployment/ollama", "--timeout=10m")
        for model in ("nomic-embed-text", "llama3.2:3b"):
            kube("exec", "deployment/ollama", "--", "ollama", "pull", model)
    finally:
        kube("delete", "networkpolicy", "ollama-model-download", "--ignore-not-found")

    kube("delete", "pod", "corpus-loader", "--ignore-not-found")
    apply({"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "corpus-loader"},
           "spec": {"automountServiceAccountToken": False,
                    "containers": [{"name": "loader", "image": f"rahbar-indexer:{IMAGE_TAG}",
                                    "imagePullPolicy": "Never", "command": ["sleep", "1800"],
                                    "securityContext": {"runAsUser": 0},
                                    "volumeMounts": [{"name": "corpus", "mountPath": "/corpus"}]}],
                    "volumes": [{"name": "corpus",
                                 "persistentVolumeClaim": {"claimName": "rahbar-corpus"}}]}})
    try:
        kube("wait", "--for=condition=Ready", "pod/corpus-loader", "--timeout=3m")
        with tempfile.TemporaryFile() as bundle:
            with tarfile.open(fileobj=bundle, mode="w") as archive:
                for file in files:
                    info = archive.gettarinfo(str(file), arcname=file.name)
                    info.mode = 0o644
                    with file.open("rb") as stream:
                        archive.addfile(info, stream)
            bundle.seek(0)
            kube("exec", "-i", "corpus-loader", "--", "tar", "xf", "-", "-C", "/corpus",
                 stdin=bundle)
    finally:
        kube("delete", "pod", "corpus-loader", "--ignore-not-found")

    kube("rollout", "status", "statefulset/chroma", "--timeout=5m")
    return job


def evaluate(port, destination):
    result = subprocess.run(
        [sys.executable, "-u", "eval/run_eval.py", "--api", f"http://127.0.0.1:{port}",
         "--baseline", str(destination.parent / "no-trial-baseline.json"),
         "--out", str(destination), "--responses", str(destination.with_name(
             destination.name.replace("results-", "responses-", 1)))],
        cwd=ROOT,
    )
    # A failed quality gate still produces measured scores. A crashed run does not.
    if not destination.exists():
        raise RuntimeError(f"Evaluator exited with {result.returncode} before writing scores.")
    return result.returncode == 0


def wait_for_index(job_name):
    deadline = time.monotonic() + 3660
    while time.monotonic() < deadline:
        status = kube("get", "job", job_name, "-o", "json", capture_output=True).stdout
        for condition in json.loads(status).get("status", {}).get("conditions", []):
            if condition["status"] != "True":
                continue
            if condition["type"] == "Complete":
                return
            if condition["type"] in {"Failed", "FailureTarget"}:
                raise RuntimeError(f"{job_name} failed: {condition.get('message', condition)}")
        time.sleep(10)
    raise TimeoutError(f"{job_name} did not finish within 61 minutes")


def trial(template, size, overlap, output):
    suffix = f"{size}-{overlap}"
    job_name = f"indexer-{suffix}"
    collection = f"rahbar-real-{suffix}"
    job = deepcopy(template)
    job["metadata"]["name"] = job_name
    job["spec"]["activeDeadlineSeconds"] = 3600
    # Preserve the failed pod and its exit reason for an evaluation attempt.
    job["spec"]["backoffLimit"] = 0
    pod_spec = job["spec"]["template"]["spec"]
    pod_spec["restartPolicy"] = "Never"
    container, = pod_spec["containers"]
    container["env"] = [{"name": name, "value": value} for name, value in {
        "CHROMA_COLLECTION": collection, "CHUNK_SIZE": str(size),
        "CHUNK_OVERLAP": str(overlap), "OMP_THREAD_LIMIT": "1",
    }.items()]
    kube("delete", "job", job_name, "--ignore-not-found")
    apply(job)
    try:
        wait_for_index(job_name)
    except (RuntimeError, TimeoutError, subprocess.CalledProcessError):
        selector = f"batch.kubernetes.io/job-name={job_name}"
        details = kube("describe", "pods", "-l", selector, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False).stdout
        diagnostics = output / f"indexer-{suffix}-pod.txt"
        diagnostics.write_bytes(details)
        print(f"Failed pod details: {diagnostics}", flush=True)
        raise
    finally:
        log = kube("logs", f"job/{job_name}", stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, check=False).stdout
        log_path = output / f"indexer-{suffix}.log"
        log_path.write_bytes(log)
        print(f"Indexer log: {log_path}", flush=True)
    counts = [json.loads(line) for line in log.splitlines() if b'"indexer finished"' in line]
    if not counts:
        raise RuntimeError(f"{job_name} finished without recording a chunk count")

    kube("set", "env", "deployment/api", f"CHROMA_COLLECTION={collection}")
    kube("rollout", "status", "deployment/api", "--timeout=8m")
    destination = output / f"results-{suffix}.json"
    with subprocess.Popen(
        [*KUBE, "port-forward", "--address", "127.0.0.1", "service/api", ":8000"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    ) as forward:
        try:
            assert forward.stdout is not None
            for line in forward.stdout:
                match = re.search(r"Forwarding from 127\.0\.0\.1:(\d+)", line)
                if match:
                    gate_passed = evaluate(match[1], destination)
                    break
                print(line, end="", flush=True)
            else:
                raise RuntimeError("kubectl port-forward did not open a local port")
        finally:
            forward.terminate()

    result = json.loads(destination.read_text(encoding="utf-8"))
    return {"chunk_size_words": size, "overlap_words": overlap,
            "chunks_indexed": counts[-1]["chunks"], "gate_passed": gate_passed,
            **{key: result[key] for key in ("recall@3", "recall@5", "citation_validity",
                                           "abstention_correctness")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", default="6144mb")
    parser.add_argument("--cpus", default="4")
    args = parser.parse_args()
    for program in ("docker", "minikube", "kubectl"):
        if shutil.which(program) is None:
            parser.error(f"{program} is missing from PATH. Reopen PowerShell after installing it.")
    files = corpus_files()
    ready = kube("--request-timeout=5s", "get", "--raw=/readyz",
                 capture_output=True, check=False)
    if ready.returncode != 0:
        run("minikube", "start", "-p", PROFILE, "--driver=docker", "--keep-context",
            "--memory", args.memory, "--cpus", args.cpus)
    for component in ("api", "indexer", "ui"):
        image = f"rahbar-{component}:{IMAGE_TAG}"
        run("docker", "build", "-t", image, component)
        run("minikube", "image", "load", "-p", PROFILE, image, "--overwrite=true")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="run-", dir=OUTPUT))
    print(f"Saving trial evidence to {output}", flush=True)
    template = prepare_stack(files)
    summary = []
    for size, overlap in TRIALS:
        summary.append(trial(template, size, overlap, output))
        print(json.dumps(summary[-1], indent=2), flush=True)
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                             encoding="utf-8")
    print(f"All three trials finished. Evidence: {output}", flush=True)


if __name__ == "__main__":
    main()
