FROM python:3.10-slim

WORKDIR /home/user/app
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/home/user/.cache/huggingface \
    TOKENIZERS_PARALLELISM=false

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py adapter_config.json adapter_model.safetensors training_manifest.json ./

RUN useradd -m -u 1000 user && chown -R user:user /home/user
USER user

EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--limit-concurrency", "4", "--timeout-keep-alive", "15"]
