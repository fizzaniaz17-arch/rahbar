FROM python:3.12.11-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx==0.28.1 PyYAML==6.0.2
COPY . ./eval
USER 10001:10001
ENTRYPOINT ["python", "-m", "eval.run_eval"]
