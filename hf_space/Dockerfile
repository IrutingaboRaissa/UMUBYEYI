FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY models/ ./models/

# Hugging Face Docker Spaces run as a non-root user by convention.
RUN useradd -m -u 1000 umubyeyi && chown -R umubyeyi:umubyeyi /app
USER umubyeyi

ENV HF_HOME=/app/.cache

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
