FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY server.py test_server.py ./
USER 10001:10001
EXPOSE 8080
CMD ["python", "server.py", "--host", "0.0.0.0", "--tokens", "/run/secrets/lab_tokens", "--db", "/state/lab.db"]
