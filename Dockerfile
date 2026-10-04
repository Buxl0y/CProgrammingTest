FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
EXPOSE 8000
CMD ["python","server.py"]