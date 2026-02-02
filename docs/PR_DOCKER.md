# PR_DOCKER: Containerización y Deployment

**Versión:** 1.0
**Prioridad:** P2 - ALTA
**Dependencias:** PR_CODIGO (P1)

---

## 1. OBJETIVO

Empaquetar PR-System para **deployment empresarial** con un solo comando.

```bash
docker compose up -d
# Listo. Sistema completo corriendo.
```

---

## 2. ARQUITECTURA DOCKER

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER COMPOSE                           │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   NGINX     │  │  PR-SYSTEM  │  │   OLLAMA    │         │
│  │   Proxy     │  │   Backend   │  │    LLM      │         │
│  │   :80/:443  │  │   :8000     │  │   :11434    │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┴────────────────┘                 │
│                          │                                  │
│  ┌───────────────────────┴───────────────────────────────┐ │
│  │                    VOLUMES                             │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │ │
│  │  │  data/  │  │ chroma/ │  │ models/ │  │ backups/│  │ │
│  │  │ SQLite  │  │   RAG   │  │ Ollama  │  │  Auto   │  │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. ESTRUCTURA DE ARCHIVOS

```
PR/
├── docker-compose.yml          # Orquestación principal
├── docker-compose.prod.yml     # Override para producción
├── docker-compose.dev.yml      # Override para desarrollo
├── .env.example                # Variables de ejemplo
│
├── docker/
│   ├── backend/
│   │   ├── Dockerfile
│   │   └── entrypoint.sh
│   ├── nginx/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   └── ssl/               # Certificados (gitignore)
│   └── ollama/
│       └── Dockerfile
│
├── main.py
├── pr_agent/
├── requirements.txt
└── index.html
```

---

## 4. IMPLEMENTACIÓN

### 4.1 docker-compose.yml (Principal)

```yaml
# docker-compose.yml

version: '3.8'

services:
  # ============================================
  # PR-SYSTEM BACKEND (FastAPI)
  # ============================================
  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    container_name: pr-backend
    restart: unless-stopped
    environment:
      - PR_SECRET_KEY=${PR_SECRET_KEY}
      - OLLAMA_URL=http://ollama:11434
      - DATA_DIR=/app/data
    volumes:
      - pr-data:/app/data
      - pr-chroma:/app/data/chroma
      - pr-uploads:/app/data/uploads
      - pr-backups:/app/data/backups
    networks:
      - pr-network
    depends_on:
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ============================================
  # OLLAMA (LLM Local)
  # ============================================
  ollama:
    image: ollama/ollama:latest
    container_name: pr-ollama
    restart: unless-stopped
    volumes:
      - ollama-models:/root/.ollama
    networks:
      - pr-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  # ============================================
  # NGINX (Proxy reverso)
  # ============================================
  nginx:
    build:
      context: .
      dockerfile: docker/nginx/Dockerfile
    container_name: pr-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
    networks:
      - pr-network
    depends_on:
      - backend

  # ============================================
  # MODELO INICIAL (one-time setup)
  # ============================================
  model-loader:
    image: curlimages/curl:latest
    container_name: pr-model-loader
    depends_on:
      ollama:
        condition: service_healthy
    networks:
      - pr-network
    entrypoint: >
      sh -c "
        echo 'Descargando modelo llama3.2...' &&
        curl -X POST http://ollama:11434/api/pull -d '{\"name\": \"llama3.2:3b\"}' &&
        echo 'Modelo listo!'
      "
    restart: "no"

# ============================================
# VOLUMES
# ============================================
volumes:
  pr-data:
    name: pr-system-data
  pr-chroma:
    name: pr-system-chroma
  pr-uploads:
    name: pr-system-uploads
  pr-backups:
    name: pr-system-backups
  ollama-models:
    name: pr-ollama-models

# ============================================
# NETWORKS
# ============================================
networks:
  pr-network:
    name: pr-system-network
    driver: bridge
```

### 4.2 docker-compose.prod.yml (Producción)

```yaml
# docker-compose.prod.yml
# Uso: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

version: '3.8'

services:
  backend:
    environment:
      - PR_ENV=production
      - LOG_LEVEL=warning
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  nginx:
    environment:
      - NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx
    volumes:
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro

  # Backup automático diario
  backup:
    image: alpine:latest
    container_name: pr-backup
    volumes:
      - pr-data:/data:ro
      - pr-backups:/backups
      - /var/backups/pr-system:/external-backups
    entrypoint: >
      sh -c "
        while true; do
          FECHA=$$(date +%Y%m%d_%H%M%S)
          tar -czf /external-backups/pr-backup-$$FECHA.tar.gz /data /backups
          find /external-backups -name 'pr-backup-*.tar.gz' -mtime +7 -delete
          sleep 86400
        done
      "
    restart: unless-stopped
    networks:
      - pr-network
```

### 4.3 docker-compose.dev.yml (Desarrollo)

```yaml
# docker-compose.dev.yml
# Uso: docker compose -f docker-compose.yml -f docker-compose.dev.yml up

version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
      target: development
    environment:
      - PR_ENV=development
      - LOG_LEVEL=debug
    volumes:
      # Hot reload: montar código fuente
      - ./main.py:/app/main.py:ro
      - ./pr_agent:/app/pr_agent:ro
      - ./index.html:/app/index.html:ro
    ports:
      - "8000:8000"  # Exponer directamente
    command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]

  nginx:
    ports:
      - "80:80"
      # Sin SSL en desarrollo
```

### 4.4 Dockerfile Backend

```dockerfile
# docker/backend/Dockerfile

# ============================================
# STAGE 1: Base
# ============================================
FROM python:3.11-slim as base

WORKDIR /app

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# STAGE 2: Dependencies
# ============================================
FROM base as dependencies

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# STAGE 3: Development
# ============================================
FROM dependencies as development

# Herramientas de desarrollo
RUN pip install --no-cache-dir \
    watchfiles \
    pytest \
    pytest-asyncio

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================
# STAGE 4: Production
# ============================================
FROM dependencies as production

# Copiar código
COPY main.py .
COPY pr_agent/ ./pr_agent/
COPY index.html .

# Crear directorios de datos
RUN mkdir -p /app/data /app/data/chroma /app/data/uploads /app/data/backups

# Usuario no-root
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Entrypoint
COPY docker/backend/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 4.5 Entrypoint Backend

```bash
#!/bin/bash
# docker/backend/entrypoint.sh

set -e

echo "=========================================="
echo "  PR-System Backend"
echo "=========================================="

# Esperar a Ollama
echo "Esperando a Ollama..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "✓ Ollama disponible"

# Inicializar base de datos
echo "Inicializando base de datos..."
python -c "from main import init_db; init_db()"
echo "✓ Base de datos lista"

# Ejecutar comando
exec "$@"
```

### 4.6 Nginx Config

```nginx
# docker/nginx/nginx.conf

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Optimizaciones
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # Upstream
    upstream backend {
        server backend:8000;
        keepalive 32;
    }

    # HTTP -> HTTPS redirect (producción)
    server {
        listen 80;
        server_name _;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            # En desarrollo, proxy directo
            # En producción, descomentar redirect:
            # return 301 https://$host$request_uri;

            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # HTTPS (producción)
    # server {
    #     listen 443 ssl http2;
    #     server_name tu-dominio.com;
    #
    #     ssl_certificate /etc/nginx/ssl/fullchain.pem;
    #     ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    #     ssl_protocols TLSv1.2 TLSv1.3;
    #     ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:...;
    #
    #     location / {
    #         proxy_pass http://backend;
    #         ...
    #     }
    # }
}
```

### 4.7 .env.example

```env
# PR-System Environment Configuration
# Copiar a .env y ajustar valores

# ============================================
# SEGURIDAD
# ============================================
# Generar con: openssl rand -hex 32
PR_SECRET_KEY=cambiar_esto_por_valor_seguro_de_64_caracteres_minimo

# ============================================
# OLLAMA
# ============================================
OLLAMA_MODEL=llama3.2:3b
# Alternativas: mistral:7b, qwen2.5:7b, phi3:mini

# ============================================
# ENTORNO
# ============================================
PR_ENV=production
LOG_LEVEL=info

# ============================================
# DOMINIO (para SSL)
# ============================================
DOMAIN=localhost
# En producción: DOMAIN=pr-system.tu-empresa.com
```

---

## 5. SCRIPTS DE ADMINISTRACIÓN

### 5.1 Makefile

```makefile
# Makefile

.PHONY: help build up down logs shell backup restore clean

# Colores
YELLOW := \033[1;33m
GREEN := \033[1;32m
NC := \033[0m

help: ## Mostrar ayuda
	@echo "$(GREEN)PR-System - Comandos disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

build: ## Construir imágenes
	docker compose build

up: ## Iniciar sistema
	docker compose up -d
	@echo "$(GREEN)PR-System iniciado en http://localhost$(NC)"

up-dev: ## Iniciar en modo desarrollo
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

down: ## Detener sistema
	docker compose down

logs: ## Ver logs
	docker compose logs -f

logs-backend: ## Ver logs del backend
	docker compose logs -f backend

shell: ## Shell en backend
	docker compose exec backend /bin/bash

backup: ## Crear backup manual
	@FECHA=$$(date +%Y%m%d_%H%M%S) && \
	docker compose exec backend tar -czf /app/data/backups/manual-$$FECHA.tar.gz \
		/app/data/pr_system.db /app/data/chroma && \
	echo "$(GREEN)Backup creado: manual-$$FECHA.tar.gz$(NC)"

restore: ## Restaurar backup (usa BACKUP=archivo.tar.gz)
	@if [ -z "$(BACKUP)" ]; then \
		echo "Uso: make restore BACKUP=archivo.tar.gz"; \
		exit 1; \
	fi
	docker compose exec backend tar -xzf /app/data/backups/$(BACKUP) -C /

clean: ## Limpiar todo (CUIDADO: elimina datos)
	docker compose down -v --remove-orphans
	docker system prune -f

status: ## Ver estado de servicios
	docker compose ps

pull-model: ## Descargar modelo Ollama
	docker compose exec ollama ollama pull llama3.2:3b

test: ## Ejecutar tests
	docker compose exec backend pytest -v
```

### 5.2 Script de Instalación

```bash
#!/bin/bash
# install.sh - Instalación rápida de PR-System

set -e

echo "=========================================="
echo "  PR-System - Instalación"
echo "=========================================="

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado"
    echo "   Instala Docker desde: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✓ Docker encontrado"

# Verificar Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose no está disponible"
    exit 1
fi
echo "✓ Docker Compose encontrado"

# Crear .env si no existe
if [ ! -f .env ]; then
    echo "Creando archivo .env..."
    cp .env.example .env

    # Generar secret key
    SECRET=$(openssl rand -hex 32)
    sed -i "s/cambiar_esto_por_valor_seguro_de_64_caracteres_minimo/$SECRET/" .env

    echo "✓ Archivo .env creado"
else
    echo "✓ Archivo .env existente"
fi

# Construir imágenes
echo ""
echo "Construyendo imágenes Docker..."
docker compose build

# Iniciar servicios
echo ""
echo "Iniciando servicios..."
docker compose up -d

# Esperar a que esté listo
echo ""
echo "Esperando a que el sistema esté listo..."
sleep 10

# Verificar salud
if curl -s http://localhost/api/health | grep -q '"estado":"ok"'; then
    echo ""
    echo "=========================================="
    echo "  ✓ PR-System instalado correctamente"
    echo "=========================================="
    echo ""
    echo "  URL: http://localhost"
    echo "  Usuario: admin"
    echo "  Contraseña: admin123"
    echo ""
    echo "  ⚠️  Cambia la contraseña del admin!"
    echo ""
else
    echo ""
    echo "⚠️  El sistema aún está iniciando..."
    echo "   Espera unos segundos y verifica en http://localhost"
fi
```

---

## 6. REQUISITOS DE HARDWARE

### Mínimos (Sin GPU)

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disco | 20 GB | 50 GB SSD |
| GPU | No requerida | - |

*Modelo sugerido sin GPU:* `llama3.2:3b` o `phi3:mini`

### Con GPU (Recomendado)

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| GPU VRAM | 6 GB | 8+ GB |
| GPU | NVIDIA GTX 1060 | NVIDIA RTX 3060+ |

*Modelo sugerido con GPU:* `llama3.2:8b` o `mistral:7b`

---

## 7. INSTALACIÓN RÁPIDA

```bash
# 1. Clonar repositorio
git clone https://github.com/srexcel/PR.git
cd PR

# 2. Instalar
chmod +x install.sh
./install.sh

# 3. Listo!
# Abrir http://localhost
```

---

## 8. COMANDOS ÚTILES

```bash
# Ver estado
make status

# Ver logs en tiempo real
make logs

# Crear backup
make backup

# Acceder al shell del backend
make shell

# Descargar modelo adicional
make pull-model MODEL=mistral:7b

# Reiniciar todo
make down && make up

# Actualizar (sin perder datos)
git pull
docker compose build
docker compose up -d
```

---

## 9. TROUBLESHOOTING

### Ollama no inicia
```bash
# Ver logs de Ollama
docker compose logs ollama

# Verificar si el modelo está descargado
docker compose exec ollama ollama list
```

### Backend no conecta a Ollama
```bash
# Verificar red
docker network inspect pr-system-network

# Probar conexión manual
docker compose exec backend curl http://ollama:11434/api/tags
```

### Sin espacio en disco
```bash
# Limpiar imágenes no usadas
docker system prune -a

# Ver uso de volúmenes
docker system df -v
```

---

## 10. CHECKLIST

- [ ] Crear estructura `docker/`
- [ ] Implementar `docker-compose.yml`
- [ ] Implementar Dockerfiles
- [ ] Crear `nginx.conf`
- [ ] Crear `.env.example`
- [ ] Crear `Makefile`
- [ ] Crear `install.sh`
- [ ] Probar build completo
- [ ] Probar instalación limpia
- [ ] Documentar troubleshooting

---

*Este documento es checkpoint v1.0 de PR_DOCKER*
*v1.1 viene después del siguiente error*
