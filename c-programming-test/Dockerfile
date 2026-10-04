FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN useradd -m -u 10001 appuser && mkdir -p /app/data /app/tmp && chown -R appuser:appuser /app
USER appuser
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python3", "server.py"]
