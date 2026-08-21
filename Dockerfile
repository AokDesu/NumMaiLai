FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Default port for web dashboard
EXPOSE 8080

# Run Web Dashboard & monitoring daemon by default
CMD ["python", "-m", "nummailai", "web", "--port", "8080"]
