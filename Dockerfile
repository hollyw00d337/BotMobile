FROM python:3.10-slim

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.31

# Labels siguiendo la especificación OCI
LABEL maintainer="BotMobile Team"
LABEL description="BotMobile - Asistente móvil con PostgreSQL, recargas celulares, pagos CoDi/SPEI y sistema completo v1.31"
LABEL version="${VERSION}"
LABEL org.opencontainers.image.title="BotMobile"
LABEL org.opencontainers.image.description="Asistente móvil con PostgreSQL, sistema de recargas, pagos CoDi/SPEI, portabilidad y soporte completo"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.vendor="BotMobile Team"
LABEL org.opencontainers.image.source="https://github.com/hollyw00d337/BotMobile"

# Variables de entorno de Python y Rasa
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RASA_HOME=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Crear usuario no-root para seguridad
RUN useradd -m -u 1001 botmobile && \
    chown -R botmobile:botmobile /app
USER botmobile

# Entrenar el modelo (con manejo de errores) - antes de cambiar de usuario
USER root
RUN rasa train --quiet || echo "Warning: Training completed with warnings"
RUN chown -R botmobile:botmobile /app/models
USER botmobile

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
