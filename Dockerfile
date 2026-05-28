FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema mínimas para ReportLab y bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear directorios de datos en tiempo de build (el volumen los sobreescribe en runtime)
RUN mkdir -p data/uploads data/reports

EXPOSE 8000
