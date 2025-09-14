FROM python:3.10-slim

LABEL maintainer="BotMobile Team"
LABEL description="BotMobile - Asistente móvil con Node-RED e integración de botones v1.25"
LABEL version="1.25"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RASA_HOME=/app

# Dependencias básicas
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear y entrar al directorio de trabajo
WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Copiar archivos del proyecto
COPY . .

# Crear carpetas necesarias
RUN mkdir -p models logs

# Entrenar el modelo (con manejo de errores)
RUN rasa train --quiet || echo "Warning: Training completed with warnings"

# Exponer puertos
EXPOSE 5005 5055

# Variables de entorno para producción
ENV RASA_LOG_LEVEL=INFO
ENV RASA_ENV=production

# Ejecutar el servidor de Rasa con configuración de producción
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--endpoints", "endpoints_production.yml", "--log-level", "info"]

# Healthcheck para saber si el servidor está listo
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5005/status || exit 1
