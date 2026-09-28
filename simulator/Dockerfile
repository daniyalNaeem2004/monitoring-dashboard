FROM python:3.12-slim

# Unbuffered stdout so `docker compose logs` shows print() output live instead
# of only flushing in large blocks.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
