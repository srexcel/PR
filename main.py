"""
PR-System Backend
Sistema de Conocimiento Vivo - Prueba de Concepto

Este archivo es el "cerebro" del sistema:
- Recibe peticiones del frontend (la página web)
- Guarda y busca documentos en el RAG (ChromaDB)
- Se comunica con el LLM (local o en la nube)
- Gestiona las incidencias y sus estados
- Autenticación JWT con roles (operario, supervisor, admin)
- Procesamiento de documentos PDF y DOCX
- Sistema de backups automáticos
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum
import chromadb
from chromadb.utils import embedding_functions
import sqlite3
import json
import os
import io
import shutil
import httpx
import uuid
import secrets

# Autenticación
from jose import JWTError, jwt
from passlib.context import CryptContext

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================

app = FastAPI(
    title="PR-System",
    description="Sistema de Conocimiento Vivo - Prueba de Concepto",
    version="1.1.0"
)

# CORS: Permite que el frontend (página web) se comunique con el backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas de archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

# ============================================================
# AUTENTICACIÓN JWT
# ============================================================

SECRET_KEY = os.environ.get("PR_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas (turno laboral)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class RolUsuario(str, Enum):
    OPERARIO = "operario"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class UsuarioCreate(BaseModel):
    username: str
    password: str
    nombre_completo: str
    rol: RolUsuario = RolUsuario.OPERARIO
    area: Optional[str] = None


class UsuarioResponse(BaseModel):
    id: str
    username: str
    nombre_completo: str
    rol: str
    area: Optional[str]


class Token(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioResponse


def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hashear_password(password: str) -> str:
    return pwd_context.hash(password)


def crear_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> dict:
    """Extrae y valida el usuario del token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    usuario = cursor.fetchone()
    conn.close()

    if usuario is None:
        raise credentials_exception
    return dict(usuario)


def requiere_rol(*roles_permitidos: str):
    """Dependency factory que verifica que el usuario tenga un rol permitido."""
    async def verificar_rol(usuario: dict = Depends(obtener_usuario_actual)):
        if usuario["rol"] not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(roles_permitidos)}"
            )
        return usuario
    return verificar_rol


# ============================================================
# BASE DE DATOS SQLite
# ============================================================

def init_db():
    """Crea las tablas de la base de datos si no existen"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, "pr_system.db"))
    cursor = conn.cursor()

    # Tabla de usuarios (NUEVO)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            rol TEXT DEFAULT 'operario',
            area TEXT,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT
        )
    """)

    # Tabla de incidencias
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidencias (
            id TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            area TEXT,
            estado TEXT DEFAULT 'abierto',
            prioridad TEXT DEFAULT 'media',
            creado_por TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT,
            solucion TEXT,
            agregado_a_rag INTEGER DEFAULT 0
        )
    """)

    # Tabla de reportes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reportes (
            id TEXT PRIMARY KEY,
            incidencia_id TEXT,
            autor TEXT NOT NULL,
            contenido TEXT NOT NULL,
            fecha TEXT,
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id)
        )
    """)

    # Tabla de documentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documentos (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT,
            fecha_subida TEXT,
            contenido_texto TEXT
        )
    """)

    # Tabla de configuración del sistema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    # Tabla de backups (NUEVO)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backups (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            fecha TEXT NOT NULL,
            tamaño_bytes INTEGER,
            tipo TEXT DEFAULT 'manual',
            ruta TEXT
        )
    """)

    # Configuración por defecto
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('llm_provider', 'ollama')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('llm_model', 'llama3')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('ollama_url', 'http://localhost:11434')")

    # Crear usuario admin por defecto si no existe
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        admin_id = str(uuid.uuid4())
        admin_hash = hashear_password("admin123")
        cursor.execute("""
            INSERT INTO usuarios (id, username, password_hash, nombre_completo, rol, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (admin_id, "admin", admin_hash, "Administrador", "admin", datetime.now().isoformat()))

    conn.commit()
    conn.close()


init_db()

# ============================================================
# ChromaDB (RAG - Base de conocimiento)
# ============================================================
# Embeddings multilingüe para mejor calidad en español

try:
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
except Exception:
    # Fallback al modelo por defecto si no se puede cargar el multilingüe
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

try:
    collection = chroma_client.get_or_create_collection(
        name="pr_knowledge_base",
        embedding_function=embedding_fn,
        metadata={"description": "Base de conocimiento PR-System"}
    )
except Exception as e:
    print(f"Error inicializando ChromaDB: {e}")
    collection = None

# ============================================================
# PROCESAMIENTO DE DOCUMENTOS PDF/DOCX
# ============================================================

def extraer_texto_pdf(contenido_bytes: bytes) -> str:
    """Extrae texto de un archivo PDF."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(contenido_bytes))
        texto = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                texto += page_text + "\n"
        return texto.strip()
    except Exception as e:
        raise ValueError(f"Error procesando PDF: {e}")


def extraer_texto_docx(contenido_bytes: bytes) -> str:
    """Extrae texto de un archivo DOCX."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(contenido_bytes))
        texto = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return texto.strip()
    except Exception as e:
        raise ValueError(f"Error procesando DOCX: {e}")


def extraer_texto_archivo(nombre: str, contenido_bytes: bytes) -> str:
    """Extrae texto de un archivo según su extensión."""
    ext = nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""

    if ext == "pdf":
        return extraer_texto_pdf(contenido_bytes)
    elif ext in ("docx", "doc"):
        return extraer_texto_docx(contenido_bytes)
    elif ext in ("txt", "md", "csv", "log", "json", "xml"):
        return contenido_bytes.decode("utf-8", errors="replace")
    else:
        # Intentar como texto plano
        try:
            return contenido_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Formato no soportado: .{ext}")


# ============================================================
# MODELOS DE DATOS (Pydantic)
# ============================================================

class EstadoIncidencia(str, Enum):
    ABIERTO = "abierto"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"


class Prioridad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class IncidenciaCreate(BaseModel):
    titulo: str
    descripcion: str
    area: Optional[str] = None
    prioridad: Prioridad = Prioridad.MEDIA
    creado_por: Optional[str] = None


class ReporteCreate(BaseModel):
    autor: str
    contenido: str


class SolucionCreate(BaseModel):
    solucion: str
    agregar_a_rag: bool = True


class ConsultaRAG(BaseModel):
    pregunta: str
    n_resultados: int = 5


class ConfiguracionLLM(BaseModel):
    provider: str
    model: str
    api_key: Optional[str] = None
    ollama_url: Optional[str] = "http://localhost:11434"


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def get_db():
    return sqlite3.connect(os.path.join(DATA_DIR, "pr_system.db"))


def get_config(clave: str) -> Optional[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def set_config(clave: str, valor: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
    conn.commit()
    conn.close()


async def consultar_llm(prompt: str, contexto: str = "") -> str:
    """Envía una consulta al LLM configurado."""
    provider = get_config("llm_provider") or "ollama"
    model = get_config("llm_model") or "llama3"

    sistema = """Eres un asistente experto del sistema PR-System.
Tu función es ayudar a resolver problemas basándote en el conocimiento histórico de la empresa.
Cuando te den contexto de casos anteriores, úsalo para dar consejos específicos.
Siempre responde en español. Sé conciso pero útil."""

    mensaje_completo = prompt
    if contexto:
        mensaje_completo = f"""CONTEXTO DE CASOS ANTERIORES:
{contexto}

CONSULTA ACTUAL:
{prompt}

Basándote en el contexto anterior, proporciona una respuesta útil."""

    try:
        if provider == "ollama":
            ollama_url = get_config("ollama_url") or "http://localhost:11434"
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={"model": model, "prompt": mensaje_completo, "system": sistema, "stream": False}
                )
                if response.status_code == 200:
                    return response.json().get("response", "Sin respuesta")
                return f"Error de Ollama: {response.status_code}"

        elif provider == "openai":
            api_key = get_config("openai_api_key")
            if not api_key:
                return "Error: No hay API key de OpenAI configurada"
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": sistema},
                            {"role": "user", "content": mensaje_completo}
                        ]
                    }
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                return f"Error de OpenAI: {response.text}"

        elif provider == "anthropic":
            api_key = get_config("anthropic_api_key")
            if not api_key:
                return "Error: No hay API key de Anthropic configurada"
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "max_tokens": 4096,
                        "system": sistema,
                        "messages": [{"role": "user", "content": mensaje_completo}]
                    }
                )
                if response.status_code == 200:
                    return response.json()["content"][0]["text"]
                return f"Error de Anthropic: {response.text}"

        return f"Proveedor '{provider}' no soportado"

    except httpx.ConnectError:
        return f"Error: No se pudo conectar a {provider}. Verifica que el servicio esté corriendo."
    except Exception as e:
        return f"Error al consultar LLM: {str(e)}"


# ============================================================
# ENDPOINTS - AUTENTICACIÓN
# ============================================================

@app.post("/api/auth/registro", response_model=Token)
async def registrar_usuario(usuario: UsuarioCreate, admin: dict = Depends(requiere_rol("admin"))):
    """Registra un nuevo usuario. Solo admins pueden crear usuarios."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    user_id = str(uuid.uuid4())
    ahora = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO usuarios (id, username, password_hash, nombre_completo, rol, area, fecha_creacion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, usuario.username, hashear_password(usuario.password),
          usuario.nombre_completo, usuario.rol.value, usuario.area, ahora))
    conn.commit()
    conn.close()

    token = crear_token(data={"sub": user_id, "rol": usuario.rol.value})
    return Token(
        access_token=token,
        token_type="bearer",
        usuario=UsuarioResponse(
            id=user_id, username=usuario.username,
            nombre_completo=usuario.nombre_completo,
            rol=usuario.rol.value, area=usuario.area
        )
    )


@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Inicia sesión y retorna un token JWT."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE username = ? AND activo = 1", (form_data.username,))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario or not verificar_password(form_data.password, usuario["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = crear_token(data={"sub": usuario["id"], "rol": usuario["rol"]})
    return Token(
        access_token=token,
        token_type="bearer",
        usuario=UsuarioResponse(
            id=usuario["id"], username=usuario["username"],
            nombre_completo=usuario["nombre_completo"],
            rol=usuario["rol"], area=usuario["area"]
        )
    )


@app.get("/api/auth/me", response_model=UsuarioResponse)
async def perfil_usuario(usuario: dict = Depends(obtener_usuario_actual)):
    """Retorna el perfil del usuario autenticado."""
    return UsuarioResponse(
        id=usuario["id"], username=usuario["username"],
        nombre_completo=usuario["nombre_completo"],
        rol=usuario["rol"], area=usuario["area"]
    )


@app.get("/api/auth/usuarios")
async def listar_usuarios(admin: dict = Depends(requiere_rol("admin"))):
    """Lista todos los usuarios. Solo admins."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre_completo, rol, area, activo, fecha_creacion FROM usuarios")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============================================================
# ENDPOINTS - INCIDENCIAS (protegidos con auth)
# ============================================================

@app.post("/api/incidencias")
async def crear_incidencia(incidencia: IncidenciaCreate, usuario: dict = Depends(obtener_usuario_actual)):
    """Crea una nueva incidencia. Requiere autenticación."""
    conn = get_db()
    cursor = conn.cursor()

    incidencia_id = str(uuid.uuid4())
    ahora = datetime.now().isoformat()
    creador = incidencia.creado_por or usuario["nombre_completo"]

    cursor.execute("""
        INSERT INTO incidencias
        (id, titulo, descripcion, area, prioridad, creado_por, fecha_creacion, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (incidencia_id, incidencia.titulo, incidencia.descripcion,
          incidencia.area, incidencia.prioridad.value, creador, ahora, ahora))

    conn.commit()
    conn.close()

    # Buscar casos similares en el RAG
    sugerencias = []
    if collection and collection.count() > 0:
        try:
            resultados = collection.query(
                query_texts=[f"{incidencia.titulo} {incidencia.descripcion}"],
                n_results=3
            )
            if resultados and resultados['documents']:
                sugerencias = [
                    {"contenido": doc, "metadata": meta}
                    for doc, meta in zip(resultados['documents'][0], resultados['metadatas'][0])
                ]
        except Exception as e:
            print(f"Error buscando en RAG: {e}")

    return {
        "id": incidencia_id,
        "mensaje": "Incidencia creada exitosamente",
        "casos_similares": sugerencias
    }


@app.get("/api/incidencias")
async def listar_incidencias(
    estado: Optional[str] = None,
    area: Optional[str] = None,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """Lista incidencias con filtros opcionales."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM incidencias WHERE 1=1"
    params = []

    if estado:
        query += " AND estado = ?"
        params.append(estado)
    if area:
        query += " AND area = ?"
        params.append(area)

    query += " ORDER BY fecha_creacion DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/incidencias/{incidencia_id}")
async def obtener_incidencia(incidencia_id: str, usuario: dict = Depends(obtener_usuario_actual)):
    """Obtiene el detalle de una incidencia con sus reportes."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM incidencias WHERE id = ?", (incidencia_id,))
    incidencia = cursor.fetchone()

    if not incidencia:
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    cursor.execute("SELECT * FROM reportes WHERE incidencia_id = ? ORDER BY fecha", (incidencia_id,))
    reportes = cursor.fetchall()
    conn.close()

    return {
        "incidencia": dict(incidencia),
        "reportes": [dict(r) for r in reportes]
    }


@app.post("/api/incidencias/{incidencia_id}/reportes")
async def agregar_reporte(incidencia_id: str, reporte: ReporteCreate, usuario: dict = Depends(obtener_usuario_actual)):
    """Agrega un reporte a una incidencia."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM incidencias WHERE id = ?", (incidencia_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    reporte_id = str(uuid.uuid4())
    ahora = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO reportes (id, incidencia_id, autor, contenido, fecha)
        VALUES (?, ?, ?, ?, ?)
    """, (reporte_id, incidencia_id, reporte.autor or usuario["nombre_completo"], reporte.contenido, ahora))

    cursor.execute("UPDATE incidencias SET fecha_actualizacion = ? WHERE id = ?", (ahora, incidencia_id))

    conn.commit()
    conn.close()
    return {"id": reporte_id, "mensaje": "Reporte agregado"}


@app.post("/api/incidencias/{incidencia_id}/resolver")
async def resolver_incidencia(
    incidencia_id: str,
    solucion: SolucionCreate,
    usuario: dict = Depends(requiere_rol("supervisor", "admin"))
):
    """Marca incidencia como resuelta. Requiere supervisor o admin."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM incidencias WHERE id = ?", (incidencia_id,))
    incidencia = cursor.fetchone()

    if not incidencia:
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    cursor.execute("SELECT * FROM reportes WHERE incidencia_id = ? ORDER BY fecha", (incidencia_id,))
    reportes = cursor.fetchall()

    ahora = datetime.now().isoformat()

    cursor.execute("""
        UPDATE incidencias
        SET estado = 'resuelto', solucion = ?, fecha_actualizacion = ?, agregado_a_rag = ?
        WHERE id = ?
    """, (solucion.solucion, ahora, 1 if solucion.agregar_a_rag else 0, incidencia_id))

    conn.commit()
    conn.close()

    # Agregar al RAG
    if solucion.agregar_a_rag and collection:
        reportes_texto = "\n".join([f"- {r['autor']}: {r['contenido']}" for r in reportes])

        documento = f"""
CASO: {incidencia['titulo']}
ÁREA: {incidencia['area'] or 'No especificada'}
FECHA: {incidencia['fecha_creacion']}

DESCRIPCIÓN DEL PROBLEMA:
{incidencia['descripcion']}

REPORTES DE INVOLUCRADOS:
{reportes_texto if reportes_texto else 'Sin reportes adicionales'}

SOLUCIÓN APLICADA:
{solucion.solucion}

RESULTADO: RESUELTO
"""
        try:
            collection.add(
                documents=[documento],
                metadatas=[{
                    "tipo": "incidencia_resuelta",
                    "titulo": incidencia['titulo'],
                    "area": incidencia['area'] or "",
                    "fecha": ahora,
                    "incidencia_id": incidencia_id
                }],
                ids=[f"inc_{incidencia_id}"]
            )
        except Exception as e:
            return {"mensaje": "Incidencia resuelta pero error al agregar al RAG", "error": str(e)}

    return {"mensaje": "Incidencia resuelta y agregada a la base de conocimiento"}


@app.post("/api/incidencias/{incidencia_id}/generar-documento")
async def generar_documento_final(incidencia_id: str, usuario: dict = Depends(obtener_usuario_actual)):
    """Genera un documento consolidado con el LLM."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM incidencias WHERE id = ?", (incidencia_id,))
    incidencia = cursor.fetchone()

    if not incidencia:
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    cursor.execute("SELECT * FROM reportes WHERE incidencia_id = ? ORDER BY fecha", (incidencia_id,))
    reportes = cursor.fetchall()
    conn.close()

    reportes_texto = "\n".join([f"Reporte de {r['autor']}:\n{r['contenido']}\n" for r in reportes])

    prompt = f"""Genera un documento formal de resolución de incidencia basado en la siguiente información:

TÍTULO: {incidencia['titulo']}
ÁREA: {incidencia['area'] or 'No especificada'}
PRIORIDAD: {incidencia['prioridad']}
FECHA DE CREACIÓN: {incidencia['fecha_creacion']}

DESCRIPCIÓN INICIAL:
{incidencia['descripcion']}

REPORTES DE INVOLUCRADOS:
{reportes_texto if reportes_texto else 'Sin reportes adicionales'}

SOLUCIÓN APLICADA:
{incidencia['solucion'] or 'Pendiente de resolución'}

Por favor genera un documento estructurado que incluya:
1. Resumen ejecutivo
2. Descripción del problema
3. Análisis de causas (basado en los reportes)
4. Acciones tomadas
5. Resultado
6. Lecciones aprendidas
7. Recomendaciones para prevenir recurrencia"""

    documento_generado = await consultar_llm(prompt)
    return {"documento": documento_generado, "incidencia_id": incidencia_id}


# ============================================================
# ENDPOINTS - RAG (Base de Conocimiento)
# ============================================================

@app.post("/api/rag/consultar")
async def consultar_rag(consulta: ConsultaRAG, usuario: dict = Depends(obtener_usuario_actual)):
    """Consulta la base de conocimiento y genera respuesta con LLM."""
    if not collection:
        raise HTTPException(status_code=500, detail="Base de conocimiento no inicializada")

    contexto = ""
    casos_encontrados = []

    if collection.count() > 0:
        try:
            resultados = collection.query(
                query_texts=[consulta.pregunta],
                n_results=consulta.n_resultados
            )
            if resultados and resultados['documents']:
                for doc, meta in zip(resultados['documents'][0], resultados['metadatas'][0]):
                    casos_encontrados.append({"contenido": doc, "metadata": meta})
                    contexto += f"\n---\n{doc}\n"
        except Exception as e:
            print(f"Error buscando en RAG: {e}")

    respuesta_llm = await consultar_llm(consulta.pregunta, contexto)

    return {
        "respuesta": respuesta_llm,
        "casos_similares": casos_encontrados,
        "total_documentos_en_rag": collection.count() if collection else 0
    }


@app.post("/api/rag/agregar-documento")
async def agregar_documento_rag(
    archivo: UploadFile = File(...),
    titulo: str = Form(...),
    tipo: str = Form("documento"),
    usuario: dict = Depends(requiere_rol("supervisor", "admin"))
):
    """
    Agrega un documento a la base de conocimiento.
    Soporta: .txt, .md, .csv, .pdf, .docx
    Requiere supervisor o admin.
    """
    if not collection:
        raise HTTPException(status_code=500, detail="Base de conocimiento no inicializada")

    contenido = await archivo.read()

    # Extraer texto según formato
    try:
        texto = extraer_texto_archivo(archivo.filename, contenido)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not texto.strip():
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del archivo")

    # Guardar archivo físico
    archivo_path = os.path.join(UPLOADS_DIR, archivo.filename)
    with open(archivo_path, 'wb') as f:
        f.write(contenido)

    doc_id = str(uuid.uuid4())
    ahora = datetime.now().isoformat()

    # Guardar en SQLite
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documentos (id, nombre, tipo, fecha_subida, contenido_texto)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, titulo, tipo, ahora, texto[:10000]))
    conn.commit()
    conn.close()

    # Agregar al RAG (dividir en chunks si es muy largo)
    try:
        max_chunk = 4000
        chunks = [texto[i:i + max_chunk] for i in range(0, len(texto), max_chunk)]
        for idx, chunk in enumerate(chunks):
            chunk_id = f"doc_{doc_id}_{idx}" if len(chunks) > 1 else f"doc_{doc_id}"
            collection.add(
                documents=[chunk],
                metadatas=[{
                    "tipo": tipo,
                    "titulo": titulo,
                    "archivo": archivo.filename,
                    "fecha": ahora,
                    "chunk": idx,
                    "total_chunks": len(chunks)
                }],
                ids=[chunk_id]
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error agregando a RAG: {e}")

    return {
        "id": doc_id,
        "mensaje": f"Documento agregado ({len(chunks)} fragmento(s))",
        "total_documentos": collection.count()
    }


@app.get("/api/rag/documentos")
async def listar_documentos(usuario: dict = Depends(obtener_usuario_actual)):
    """Lista todos los documentos en la base de conocimiento."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, tipo, fecha_subida FROM documentos ORDER BY fecha_subida DESC")
    rows = cursor.fetchall()

    cursor.execute("""
        SELECT id, titulo, area, fecha_creacion
        FROM incidencias WHERE agregado_a_rag = 1 ORDER BY fecha_creacion DESC
    """)
    incidencias = cursor.fetchall()
    conn.close()

    return {
        "documentos": [dict(row) for row in rows],
        "incidencias_en_rag": [dict(i) for i in incidencias],
        "total": collection.count() if collection else 0
    }


@app.get("/api/rag/stats")
async def estadisticas_rag(usuario: dict = Depends(obtener_usuario_actual)):
    """Estadísticas de la base de conocimiento."""
    return {
        "total_documentos": collection.count() if collection else 0,
        "estado": "activo" if collection else "inactivo"
    }


# ============================================================
# ENDPOINTS - BACKUPS
# ============================================================

@app.post("/api/backups/crear")
async def crear_backup(admin: dict = Depends(requiere_rol("admin"))):
    """Crea un backup completo (SQLite + ChromaDB). Solo admin."""
    backup_id = str(uuid.uuid4())
    ahora = datetime.now()
    nombre = f"backup_{ahora.strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join(BACKUPS_DIR, nombre)
    os.makedirs(backup_path, exist_ok=True)

    # Backup SQLite
    db_src = os.path.join(DATA_DIR, "pr_system.db")
    db_dst = os.path.join(backup_path, "pr_system.db")
    src_conn = sqlite3.connect(db_src)
    dst_conn = sqlite3.connect(db_dst)
    src_conn.backup(dst_conn)
    src_conn.close()
    dst_conn.close()

    # Backup ChromaDB
    chroma_dst = os.path.join(backup_path, "chroma")
    if os.path.exists(CHROMA_DIR):
        shutil.copytree(CHROMA_DIR, chroma_dst)

    # Calcular tamaño
    total_size = 0
    for dirpath, _, filenames in os.walk(backup_path):
        for f in filenames:
            total_size += os.path.getsize(os.path.join(dirpath, f))

    # Registrar backup
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO backups (id, nombre, fecha, tamaño_bytes, tipo, ruta)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (backup_id, nombre, ahora.isoformat(), total_size, "manual", backup_path))
    conn.commit()
    conn.close()

    return {
        "id": backup_id,
        "nombre": nombre,
        "tamaño_mb": round(total_size / (1024 * 1024), 2),
        "mensaje": "Backup creado exitosamente"
    }


@app.get("/api/backups")
async def listar_backups(admin: dict = Depends(requiere_rol("admin"))):
    """Lista todos los backups disponibles."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backups ORDER BY fecha DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/backups/{backup_id}/restaurar")
async def restaurar_backup(backup_id: str, admin: dict = Depends(requiere_rol("admin"))):
    """Restaura un backup. Solo admin."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backups WHERE id = ?", (backup_id,))
    backup = cursor.fetchone()
    conn.close()

    if not backup:
        raise HTTPException(status_code=404, detail="Backup no encontrado")

    backup_path = backup["ruta"]
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Archivos de backup no encontrados en disco")

    # Restaurar SQLite
    db_backup = os.path.join(backup_path, "pr_system.db")
    db_target = os.path.join(DATA_DIR, "pr_system.db")
    if os.path.exists(db_backup):
        shutil.copy2(db_backup, db_target)

    # Restaurar ChromaDB
    chroma_backup = os.path.join(backup_path, "chroma")
    if os.path.exists(chroma_backup):
        if os.path.exists(CHROMA_DIR):
            shutil.rmtree(CHROMA_DIR)
        shutil.copytree(chroma_backup, CHROMA_DIR)

    return {"mensaje": "Backup restaurado. Reiniciar el servidor para aplicar cambios."}


@app.get("/api/backups/{backup_id}/descargar")
async def descargar_backup(backup_id: str, admin: dict = Depends(requiere_rol("admin"))):
    """Descarga un backup como archivo ZIP."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backups WHERE id = ?", (backup_id,))
    backup = cursor.fetchone()
    conn.close()

    if not backup:
        raise HTTPException(status_code=404, detail="Backup no encontrado")

    backup_path = backup["ruta"]
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Archivos no encontrados")

    # Crear ZIP en memoria
    zip_path = backup_path + ".zip"
    shutil.make_archive(backup_path, 'zip', backup_path)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{backup['nombre']}.zip"
    )


# ============================================================
# ENDPOINTS - CONFIGURACIÓN
# ============================================================

@app.get("/api/configuracion")
async def obtener_configuracion(usuario: dict = Depends(obtener_usuario_actual)):
    """Obtiene la configuración actual del sistema."""
    return {
        "llm_provider": get_config("llm_provider") or "ollama",
        "llm_model": get_config("llm_model") or "llama3",
        "ollama_url": get_config("ollama_url") or "http://localhost:11434",
        "tiene_openai_key": bool(get_config("openai_api_key")),
        "tiene_anthropic_key": bool(get_config("anthropic_api_key"))
    }


@app.post("/api/configuracion")
async def actualizar_configuracion(config: ConfiguracionLLM, admin: dict = Depends(requiere_rol("admin"))):
    """Actualiza la configuración del LLM. Solo admin."""
    set_config("llm_provider", config.provider)
    set_config("llm_model", config.model)

    if config.ollama_url:
        set_config("ollama_url", config.ollama_url)

    if config.api_key:
        if config.provider == "openai":
            set_config("openai_api_key", config.api_key)
        elif config.provider == "anthropic":
            set_config("anthropic_api_key", config.api_key)

    return {"mensaje": "Configuración actualizada"}


@app.get("/api/configuracion/test-llm")
async def probar_conexion_llm(usuario: dict = Depends(obtener_usuario_actual)):
    """Prueba la conexión con el LLM configurado."""
    respuesta = await consultar_llm("Di 'Hola, estoy funcionando correctamente' y nada más.")
    return {
        "exito": "error" not in respuesta.lower(),
        "respuesta": respuesta
    }


# ============================================================
# ENDPOINT DE SALUD (público, sin auth)
# ============================================================

@app.get("/api/health")
async def health_check():
    """Verifica que el sistema está funcionando."""
    return {
        "estado": "ok",
        "version": "1.1.0",
        "base_datos": "ok",
        "rag": "ok" if collection else "no inicializado",
        "documentos_en_rag": collection.count() if collection else 0
    }


# ============================================================
# PR-AGENT ENDPOINTS
# ============================================================

from pr_agent import PRAgent

# Inicializar agente PR
pr_agent = PRAgent(
    rag_collection=collection,
    db_path=os.path.join(DATA_DIR, "pr_system.db"),
    llm_func=consultar_llm
)


class ProblemaRequest(BaseModel):
    descripcion: str
    area: str
    prioridad: Optional[str] = "media"


class ResolverRequest(BaseModel):
    solucion: str
    causa_raiz: str
    acciones_preventivas: str
    agregar_a_rag: bool = True


class ConsultaPRRequest(BaseModel):
    pregunta: str
    area: Optional[str] = None
    n_resultados: int = 5


@app.post("/api/pr/problema")
async def recibir_problema_pr(
    request: ProblemaRequest,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Endpoint principal PR: Recibe problema e inicia ciclo.

    El agente PR:
    1. Crea checkpoint
    2. Busca casos similares en RAG
    3. Si hay similares → Los muestra con análisis
    4. Si es nuevo → Guía documentación

    Implementa ANTES: ¿Dónde estoy?
    """
    resultado = await pr_agent.recibir_problema(
        descripcion=request.descripcion,
        area=request.area,
        usuario=usuario["nombre_completo"],
        prioridad=request.prioridad
    )
    return resultado


@app.post("/api/pr/resolver/{incidencia_id}")
async def resolver_pr(
    incidencia_id: str,
    request: ResolverRequest,
    usuario: dict = Depends(requiere_rol("supervisor", "admin"))
):
    """
    Cierra ciclo PR: Resuelve y hereda conocimiento.

    El agente PR:
    1. Crea nueva versión (ej: SOLDADURA_v1.3)
    2. Guarda en RAG para futuros casos
    3. Actualiza incidencia

    Implementa DESPUÉS: ¿Qué aprendí?
    """
    resultado = await pr_agent.resolver_incidencia(
        incidencia_id=incidencia_id,
        solucion=request.solucion,
        causa_raiz=request.causa_raiz,
        acciones_preventivas=request.acciones_preventivas,
        usuario=usuario["nombre_completo"],
        agregar_a_rag=request.agregar_a_rag
    )
    return resultado


@app.post("/api/pr/consultar")
async def consultar_pr(
    request: ConsultaPRRequest,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Consulta la base de conocimiento con RAG + LLM.

    Busca casos similares y genera respuesta contextualizada
    usando el conocimiento histórico de la empresa.
    """
    resultado = await pr_agent.consultar(
        pregunta=request.pregunta,
        area=request.area,
        n_resultados=request.n_resultados
    )
    return resultado


@app.get("/api/pr/versiones")
async def listar_versiones_pr(
    area: Optional[str] = None,
    tipo: Optional[str] = None,
    limite: int = 50,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Lista versiones de conocimiento.

    Muestra la evolución del conocimiento:
    SOLDADURA_v1.0 → SOLDADURA_v1.1 → SOLDADURA_v1.2 → ...
    """
    return pr_agent.versiones.listar_versiones(
        area=area,
        tipo=tipo,
        limite=limite
    )


@app.get("/api/pr/versiones/{area}/historial")
async def historial_area_pr(
    area: str,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Obtiene historial completo de un área.

    Muestra toda la evolución del conocimiento en esa área.
    """
    return pr_agent.obtener_historial_area(area)


@app.get("/api/pr/estadisticas")
async def estadisticas_pr(
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Estadísticas del sistema PR.

    Incluye:
    - Total de documentos en memoria
    - Versiones por área
    - Checkpoints activos
    """
    return pr_agent.obtener_estadisticas()


@app.post("/api/pr/incidencias/{incidencia_id}/documento-8d")
async def generar_documento_8d_pr(
    incidencia_id: str,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Genera documento 8D para una incidencia resuelta.

    Usa LLM para crear documento profesional con:
    D1-D8 completos según metodología 8D.
    """
    return await pr_agent.generar_documento_8d(incidencia_id)


@app.post("/api/pr/incidencias/{incidencia_id}/reportes")
async def agregar_reporte_pr(
    incidencia_id: str,
    reporte: ReporteCreate,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """Agrega un reporte a una incidencia usando PR-Agent"""
    return await pr_agent.agregar_reporte(
        incidencia_id=incidencia_id,
        contenido=reporte.contenido,
        autor=reporte.autor or usuario["nombre_completo"]
    )


# ============================================================
# SERVIR FRONTEND
# ============================================================

INDEX_FILE = os.path.join(BASE_DIR, "index.html")


@app.get("/")
async def root():
    if os.path.exists(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return {"mensaje": "PR-System API v1.1.0 - Frontend no encontrado"}
