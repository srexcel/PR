# PR_ENTERPRISE: Deployment Empresarial

**Versión:** 1.0
**Prioridad:** P3 - MEDIA
**Dependencias:** PR_DOCKER (P2), PR_OLLAMA (P3)

---

## 1. OBJETIVO

Guía para **implementar PR-System en entornos empresariales** considerando:
- Seguridad y compliance
- Alta disponibilidad
- Escalabilidad
- Integración con sistemas existentes
- Soporte y mantenimiento

---

## 2. ARQUITECTURA EMPRESARIAL

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ZONA DMZ                                    │
│  ┌─────────────┐                                                    │
│  │   NGINX     │ ← HTTPS/443                                        │
│  │ Load Balancer│                                                   │
│  └──────┬──────┘                                                    │
└─────────┼───────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────────────┐
│         │              ZONA APLICACIÓN                              │
│         ▼                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ PR-Backend  │  │ PR-Backend  │  │ PR-Backend  │  (Replicas)     │
│  │   :8000     │  │   :8000     │  │   :8000     │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         └────────────────┼────────────────┘                         │
│                          ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    OLLAMA CLUSTER                            │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                      │   │
│  │  │ Ollama  │  │ Ollama  │  │ Ollama  │  (GPU Nodes)         │   │
│  │  │ Node 1  │  │ Node 2  │  │ Node 3  │                      │   │
│  │  └─────────┘  └─────────┘  └─────────┘                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────────────┐
│         │              ZONA DATOS                                   │
│         ▼                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  PostgreSQL │  │  ChromaDB   │  │   MinIO     │                 │
│  │  (Primary)  │  │  (Vector)   │  │  (Backups)  │                 │
│  └──────┬──────┘  └─────────────┘  └─────────────┘                 │
│         │                                                           │
│  ┌──────┴──────┐                                                    │
│  │  PostgreSQL │  (Replica - Read)                                  │
│  └─────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. REQUISITOS EMPRESARIALES

### 3.1 Hardware (Producción)

| Componente | Mínimo | Recomendado | Alta Disponibilidad |
|------------|--------|-------------|---------------------|
| Servidores Backend | 1 | 2 | 3+ |
| Servidores Ollama | 1 GPU | 2 GPU | 3+ GPU |
| RAM por servidor | 16 GB | 32 GB | 64 GB |
| Storage | 100 GB SSD | 500 GB SSD | 1 TB NVMe |
| GPU (Ollama) | RTX 3060 | RTX 4070 | A100/H100 |

### 3.2 Red

| Puerto | Servicio | Acceso |
|--------|----------|--------|
| 443 | HTTPS (Nginx) | Público/VPN |
| 8000 | Backend API | Interno |
| 11434 | Ollama | Interno |
| 5432 | PostgreSQL | Interno |
| 9000 | MinIO | Interno |

### 3.3 Software

- Docker 24+
- Docker Compose 2.20+
- NVIDIA Driver 535+ (para GPU)
- NVIDIA Container Toolkit

---

## 4. SEGURIDAD

### 4.1 Autenticación

```python
# Configuración de seguridad mejorada

# 1. Forzar HTTPS
SECURE_PROXY_SSL_HEADER = True

# 2. Tokens más seguros
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Reducir de 480 a 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 3. Rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...

# 4. Password policy
def validar_password(password: str) -> bool:
    if len(password) < 12:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True
```

### 4.2 Nginx Hardening

```nginx
# docker/nginx/nginx-enterprise.conf

# Seguridad headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

# SSL configuración segura
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_stapling on;
ssl_stapling_verify on;

# Rate limiting
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

location /api/auth/login {
    limit_req zone=login burst=3 nodelay;
    proxy_pass http://backend;
}
```

### 4.3 Auditoría

```python
# Agregar a main.py

from datetime import datetime
import json

class AuditLog:
    """Sistema de auditoría para compliance"""

    @staticmethod
    async def log(
        usuario_id: str,
        accion: str,
        recurso: str,
        detalles: dict = None,
        ip: str = None
    ):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log
            (timestamp, usuario_id, accion, recurso, detalles, ip)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            usuario_id,
            accion,
            recurso,
            json.dumps(detalles) if detalles else None,
            ip
        ))
        conn.commit()
        conn.close()

# Uso en endpoints
@app.post("/api/incidencias/{id}/resolver")
async def resolver_incidencia(..., request: Request):
    # ... lógica ...

    await AuditLog.log(
        usuario_id=usuario["id"],
        accion="RESOLVER_INCIDENCIA",
        recurso=f"incidencia:{incidencia_id}",
        detalles={"solucion": solucion[:100]},
        ip=request.client.host
    )
```

---

## 5. ALTA DISPONIBILIDAD

### 5.1 Docker Compose HA

```yaml
# docker-compose.ha.yml

version: '3.8'

services:
  # Load Balancer
  nginx:
    image: nginx:alpine
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.role == manager
    ports:
      - "80:80"
      - "443:443"
    networks:
      - pr-network

  # Backend con réplicas
  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - pr-network

  # PostgreSQL Primary
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: pr_system
      POSTGRES_USER: pr_admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    deploy:
      placement:
        constraints:
          - node.labels.db == primary
    networks:
      - pr-network

  # PostgreSQL Replica
  postgres-replica:
    image: postgres:15
    environment:
      POSTGRES_PRIMARY_HOST: postgres-primary
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.db == replica
    networks:
      - pr-network

  # Ollama con GPU affinity
  ollama:
    image: ollama/ollama:latest
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.labels.gpu == true
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - pr-network

networks:
  pr-network:
    driver: overlay
    attachable: true

volumes:
  postgres-data:
    driver: local
```

### 5.2 Health Checks Avanzados

```python
# health.py

from fastapi import APIRouter
import httpx
import asyncio

router = APIRouter()

@router.get("/api/health/detailed")
async def health_detailed():
    """Health check detallado para monitoreo"""

    checks = {}

    # Check Database
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # Check ChromaDB
    try:
        count = collection.count() if collection else 0
        checks["chromadb"] = {"status": "ok", "documents": count}
    except Exception as e:
        checks["chromadb"] = {"status": "error", "detail": str(e)}

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{get_config('ollama_url')}/api/tags")
            if response.status_code == 200:
                checks["ollama"] = {"status": "ok"}
            else:
                checks["ollama"] = {"status": "degraded"}
    except Exception as e:
        checks["ollama"] = {"status": "error", "detail": str(e)}

    # Status general
    all_ok = all(c.get("status") == "ok" for c in checks.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }
```

---

## 6. INTEGRACIÓN EMPRESARIAL

### 6.1 Single Sign-On (SSO)

```python
# sso.py - Integración con Active Directory / LDAP

from ldap3 import Server, Connection, ALL

class LDAPAuth:
    def __init__(self):
        self.server = Server(
            os.getenv("LDAP_SERVER"),
            get_info=ALL
        )
        self.base_dn = os.getenv("LDAP_BASE_DN")

    async def authenticate(self, username: str, password: str) -> dict:
        """Autenticar contra LDAP/AD"""
        user_dn = f"uid={username},{self.base_dn}"

        try:
            conn = Connection(
                self.server,
                user=user_dn,
                password=password,
                auto_bind=True
            )

            # Buscar información del usuario
            conn.search(
                self.base_dn,
                f"(uid={username})",
                attributes=['cn', 'mail', 'memberOf']
            )

            if conn.entries:
                entry = conn.entries[0]
                return {
                    "username": username,
                    "nombre_completo": str(entry.cn),
                    "email": str(entry.mail),
                    "grupos": [str(g) for g in entry.memberOf]
                }

            return None

        except Exception as e:
            print(f"LDAP auth error: {e}")
            return None
```

### 6.2 Webhook para ERP/MES

```python
# webhooks.py

import httpx
from typing import Optional

class WebhookManager:
    """Envía eventos a sistemas externos"""

    def __init__(self):
        self.endpoints = {
            "erp": os.getenv("WEBHOOK_ERP_URL"),
            "mes": os.getenv("WEBHOOK_MES_URL"),
            "email": os.getenv("WEBHOOK_EMAIL_URL"),
        }

    async def emit(
        self,
        event_type: str,
        data: dict,
        targets: Optional[list] = None
    ):
        """Emite evento a sistemas configurados"""

        payload = {
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "source": "pr-system"
        }

        targets = targets or list(self.endpoints.keys())

        async with httpx.AsyncClient() as client:
            for target in targets:
                url = self.endpoints.get(target)
                if url:
                    try:
                        await client.post(
                            url,
                            json=payload,
                            timeout=10.0
                        )
                    except Exception as e:
                        print(f"Webhook {target} failed: {e}")

# Uso
webhooks = WebhookManager()

@app.post("/api/incidencias/{id}/resolver")
async def resolver_incidencia(...):
    # ... resolver ...

    # Notificar a ERP
    await webhooks.emit(
        "incidencia.resuelta",
        {
            "incidencia_id": incidencia_id,
            "area": incidencia["area"],
            "version": version,
            "resuelto_por": usuario["nombre_completo"]
        },
        targets=["erp", "email"]
    )
```

### 6.3 API para Sistemas Externos

```python
# api_externa.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

router = APIRouter(prefix="/api/v1/external")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verifica API key para integraciones"""
    valid_keys = get_config("external_api_keys").split(",")
    if api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@router.post("/incidencias", dependencies=[Depends(verify_api_key)])
async def crear_incidencia_externa(data: dict):
    """Endpoint para crear incidencias desde sistemas externos"""
    # Validar datos mínimos
    required = ["titulo", "descripcion", "area", "origen"]
    for field in required:
        if field not in data:
            raise HTTPException(400, f"Campo requerido: {field}")

    # Crear incidencia
    resultado = await pr_agent.recibir_problema(
        descripcion=data["descripcion"],
        area=data["area"],
        usuario=f"external:{data['origen']}"
    )

    return resultado

@router.get("/conocimiento/buscar", dependencies=[Depends(verify_api_key)])
async def buscar_conocimiento_externo(query: str, limit: int = 5):
    """Buscar en base de conocimiento desde sistemas externos"""
    resultado = await pr_agent.memoria.buscar_similares(
        query=query,
        n_resultados=limit
    )
    return {"resultados": resultado}
```

---

## 7. MONITOREO Y ALERTAS

### 7.1 Prometheus Metrics

```python
# metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Métricas
REQUESTS_TOTAL = Counter(
    'pr_requests_total',
    'Total de requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'pr_request_duration_seconds',
    'Duración de requests',
    ['endpoint']
)

INCIDENCIAS_ACTIVAS = Gauge(
    'pr_incidencias_activas',
    'Número de incidencias activas'
)

RAG_DOCUMENTS = Gauge(
    'pr_rag_documents_total',
    'Total de documentos en RAG'
)

@app.get("/metrics")
async def metrics():
    """Endpoint de métricas para Prometheus"""
    # Actualizar gauges
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM incidencias WHERE estado != 'cerrado'")
    INCIDENCIAS_ACTIVAS.set(cursor.fetchone()[0])
    conn.close()

    RAG_DOCUMENTS.set(collection.count() if collection else 0)

    return Response(
        generate_latest(),
        media_type="text/plain"
    )
```

### 7.2 Alertas

```yaml
# alertmanager/rules.yml

groups:
  - name: pr-system
    rules:
      - alert: PRSystemDown
        expr: up{job="pr-backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PR-System backend está caído"

      - alert: OllamaUnhealthy
        expr: pr_ollama_healthy == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Ollama no responde"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, pr_request_duration_seconds) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Tiempo de respuesta alto (>5s p95)"

      - alert: RAGEmpty
        expr: pr_rag_documents_total == 0
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Base de conocimiento vacía"
```

---

## 8. BACKUP Y DISASTER RECOVERY

### 8.1 Estrategia de Backups

| Tipo | Frecuencia | Retención | Destino |
|------|------------|-----------|---------|
| Incremental | Cada hora | 24 horas | Local |
| Diario | 00:00 | 30 días | NAS/S3 |
| Semanal | Domingo | 12 semanas | Offsite |
| Mensual | Día 1 | 12 meses | Offsite |

### 8.2 Script de Backup

```bash
#!/bin/bash
# backup-enterprise.sh

set -e

FECHA=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/pr-system"
S3_BUCKET="s3://empresa-backups/pr-system"

echo "=== Backup PR-System $FECHA ==="

# 1. Backup PostgreSQL
echo "Backup PostgreSQL..."
docker compose exec -T postgres-primary pg_dump -U pr_admin pr_system | \
    gzip > "$BACKUP_DIR/postgres-$FECHA.sql.gz"

# 2. Backup ChromaDB
echo "Backup ChromaDB..."
docker compose exec -T backend tar -czf - /app/data/chroma | \
    cat > "$BACKUP_DIR/chroma-$FECHA.tar.gz"

# 3. Backup configuración
echo "Backup configuración..."
tar -czf "$BACKUP_DIR/config-$FECHA.tar.gz" \
    docker-compose.yml .env docker/

# 4. Subir a S3
echo "Subiendo a S3..."
aws s3 cp "$BACKUP_DIR/postgres-$FECHA.sql.gz" "$S3_BUCKET/daily/"
aws s3 cp "$BACKUP_DIR/chroma-$FECHA.tar.gz" "$S3_BUCKET/daily/"

# 5. Limpiar backups locales antiguos
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "=== Backup completado ==="
```

### 8.3 Procedimiento de Restore

```bash
#!/bin/bash
# restore-enterprise.sh

BACKUP_DATE=$1

if [ -z "$BACKUP_DATE" ]; then
    echo "Uso: ./restore.sh YYYYMMDD_HHMMSS"
    exit 1
fi

echo "=== Restaurando backup $BACKUP_DATE ==="

# 1. Detener servicios
docker compose stop backend

# 2. Restaurar PostgreSQL
echo "Restaurando PostgreSQL..."
gunzip -c "/backups/pr-system/postgres-$BACKUP_DATE.sql.gz" | \
    docker compose exec -T postgres-primary psql -U pr_admin pr_system

# 3. Restaurar ChromaDB
echo "Restaurando ChromaDB..."
docker compose exec -T backend rm -rf /app/data/chroma
docker compose exec -T backend tar -xzf - -C / < \
    "/backups/pr-system/chroma-$BACKUP_DATE.tar.gz"

# 4. Reiniciar servicios
docker compose start backend

echo "=== Restore completado ==="
```

---

## 9. CHECKLIST DE DEPLOYMENT

### Pre-Deployment
- [ ] Revisar requisitos de hardware
- [ ] Configurar red y firewall
- [ ] Preparar certificados SSL
- [ ] Configurar DNS
- [ ] Preparar secrets y API keys

### Deployment
- [ ] Clonar repositorio
- [ ] Configurar .env con valores de producción
- [ ] Ejecutar docker compose (HA)
- [ ] Verificar health checks
- [ ] Descargar modelo Ollama

### Post-Deployment
- [ ] Cambiar contraseña admin
- [ ] Configurar SSO (si aplica)
- [ ] Configurar webhooks
- [ ] Configurar backups automáticos
- [ ] Configurar monitoreo
- [ ] Documentar runbook

### Validación
- [ ] Test de carga
- [ ] Test de failover
- [ ] Test de restore
- [ ] Validar métricas
- [ ] Validar alertas

---

## 10. SOPORTE

### Niveles de Soporte

| Nivel | Descripción | SLA |
|-------|-------------|-----|
| L1 | Usuarios finales | 4h respuesta |
| L2 | Administradores | 2h respuesta |
| L3 | Desarrollo | 8h respuesta |

### Contactos

```
Soporte Técnico: soporte@tu-empresa.com
Emergencias: +52 XXX XXX XXXX
Documentación: https://docs.pr-system.local
```

---

*Este documento es checkpoint v1.0 de PR_ENTERPRISE*
*v1.1 viene después del siguiente error*
