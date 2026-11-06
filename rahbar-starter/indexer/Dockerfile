FROM python:3.12.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv/rahbar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
USER 10001:10001
COPY pipeline ./pipeline
ENTRYPOINT ["python", "-m", "pipeline.run"]
