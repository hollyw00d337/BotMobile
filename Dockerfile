FROM python:3.10-slim

LABEL maintainer="Spotybot Team"
LABEL description="Spotybot - Asistente móvil para servicios de telecomunicaciones"
LABEL version="1.11"

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

# Descargar modelo de idioma para spaCy
RUN python -m spacy download es_core_news_sm

# Copiar archivos del proyecto
COPY . .

# Crear carpetas necesarias (aunque normalmente ya estén)
RUN mkdir -p models logs

# Entrenar el modelo (esto debe hacerse después de copiar los archivos)
RUN rasa train

# Exponer puertos
EXPOSE 5005 5055

# Ejecutar el servidor de Rasa
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]

# Healthcheck para saber si el servidor está listo
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5005/status || exit 1
