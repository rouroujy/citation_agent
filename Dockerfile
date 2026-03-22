FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# 不用代理，不用国内源
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "api.server:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000","--timeout", "300"]