FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=5000
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt && useradd --create-home --uid 10001 campusfind
COPY --chown=campusfind:campusfind . .
RUN mkdir -p /app/instance/uploads && chown -R campusfind:campusfind /app/instance
USER campusfind
VOLUME ["/app/instance"]
EXPOSE 5000
CMD ["python", "scripts/docker_start.py"]
