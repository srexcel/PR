"""
PR-System Backend
Sistema de Conocimiento Vivo - Prueba de Concepto

Este archivo es el "cerebro" del sistema:
- Recibe peticiones del frontend (la página web)
- Guarda y busca documentos en el RAG (ChromaDB)
- Se comunica con el LLM (local o en la nube)
- Gestiona las incidencias y sus estados
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import chromadb
from chromadb.utils import embedding_functions
import sqlite3
import json
import os
import httpx
import uuid

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================

app = FastAPI(
    title="PR-System",
    description="Sistema de Conocimiento Vivo - Prueba de Concepto",
    version="1.0.0"
)

# CORS: Permite que el frontend (página web) se comunique con el backend
# Sin esto, el navegador bloquearía las peticiones por seguridad
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

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ============================================================
# BASE DE DATOS SQLite (para incidencias)
# ============================================================
# SQLite es una base de datos simple en un archivo
# Guarda información estructurada: quién, cuándo, qué estado

def init_db():
    """Crea las tablas de la base de datos si no existen"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, "pr_system.db"))
    cursor = conn.cursor()
    
    # Tabla de incidencias (casos/problemas reportados)
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
    
    # Tabla de reportes (cada persona puede agregar su versión)
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
    
    # Tabla de documentos (archivos subidos al RAG)
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
    
    # Configuración por defecto
    cursor.execute("""
        INSERT OR IGNORE INTO configuracion (clave, valor) 
        VALUES ('llm_provider', 'ollama')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO configuracion (clave, valor) 
        VALUES ('llm_model', 'llama3')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO configuracion (clave, valor) 
        VALUES ('ollama_url', 'http://localhost:11434')
    """)
    
    conn.commit()
    conn.close()

init_db()

# ============================================================
# ChromaDB (RAG - Base de conocimiento)
# ============================================================
# ChromaDB guarda los documentos como "vectores" (embeddings)
# Esto permite buscar por significado, no solo por palabras exactas

# Cliente de ChromaDB (persistente = guarda en disco)
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# Función de embeddings (convierte texto a vectores)
# Usamos el modelo por defecto de ChromaDB (all-MiniLM-L6-v2)
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Colección principal de documentos
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
# MODELOS DE DATOS (Pydantic)
# ============================================================
# Estos modelos definen la estructura de los datos que recibimos/enviamos
# Pydantic valida automáticamente que los datos sean correctos

class EstadoIncidencia(str, Enum):
    """Estados posibles de una incidencia"""
    ABIERTO = "abierto"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"

class Prioridad(str, Enum):
    """Niveles de prioridad"""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

class IncidenciaCreate(BaseModel):
    """Datos para crear una nueva incidencia"""
    titulo: str
    descripcion: str
    area: Optional[str] = None
    prioridad: Prioridad = Prioridad.MEDIA
    creado_por: Optional[str] = None

class ReporteCreate(BaseModel):
    """Datos para agregar un reporte a una incidencia"""
    autor: str
    contenido: str

class SolucionCreate(BaseModel):
    """Datos para marcar una incidencia como resuelta"""
    solucion: str
    agregar_a_rag: bool = True

class ConsultaRAG(BaseModel):
    """Datos para hacer una consulta al sistema"""
    pregunta: str
    n_resultados: int = 5

class ConfiguracionLLM(BaseModel):
    """Configuración del proveedor de LLM"""
    provider: str  # 'ollama', 'openai', 'anthropic'
    model: str
    api_key: Optional[str] = None
    ollama_url: Optional[str] = "http://localhost:11434"

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def get_db():
    """Obtiene conexión a la base de datos"""
    return sqlite3.connect(os.path.join(DATA_DIR, "pr_system.db"))

def get_config(clave: str) -> Optional[str]:
    """Obtiene un valor de configuración"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_config(clave: str, valor: str):
    """Guarda un valor de configuración"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
        (clave, valor)
    )
    conn.commit()
    conn.close()

async def consultar_llm(prompt: str, contexto: str = "") -> str:
    """
    Envía una consulta al LLM configurado.
    
    Args:
        prompt: La pregunta o instrucción
        contexto: Documentos relevantes del RAG para dar contexto
    
    Returns:
        Respuesta del LLM
    """
    provider = get_config("llm_provider") or "ollama"
    model = get_config("llm_model") or "llama3"
    
    # Construir el prompt completo con contexto
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
            # Ollama es un servidor local que corre LLMs
            ollama_url = get_config("ollama_url") or "http://localhost:11434"
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": mensaje_completo,
                        "system": sistema,
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return response.json().get("response", "Sin respuesta")
                else:
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
                else:
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
                        "messages": [
                            {"role": "user", "content": mensaje_completo}
                        ]
                    }
                )
                if response.status_code == 200:
                    return response.json()["content"][0]["text"]
                else:
                    return f"Error de Anthropic: {response.text}"
        
        else:
            return f"Proveedor '{provider}' no soportado"
            
    except httpx.ConnectError:
        return f"Error: No se pudo conectar a {provider}. Verifica que el servicio esté corriendo."
    except Exception as e:
        return f"Error al consultar LLM: {str(e)}"

# ============================================================
# ENDPOINTS - INCIDENCIAS
# ============================================================

@app.post("/api/incidencias")
async def crear_incidencia(incidencia: IncidenciaCreate):
    """
    Crea una nueva incidencia.
    
    El flujo es:
    1. Usuario reporta un problema
    2. Sistema guarda la incidencia
    3. Sistema busca casos similares en el RAG
    4. Retorna la incidencia + sugerencias
    """
    conn = get_db()
    cursor = conn.cursor()
    
    incidencia_id = str(uuid.uuid4())
    ahora = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO incidencias 
        (id, titulo, descripcion, area, prioridad, creado_por, fecha_creacion, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incidencia_id,
        incidencia.titulo,
        incidencia.descripcion,
        incidencia.area,
        incidencia.prioridad.value,
        incidencia.creado_por,
        ahora,
        ahora
    ))
    
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
                    {
                        "contenido": doc,
                        "metadata": meta
                    }
                    for doc, meta in zip(
                        resultados['documents'][0],
                        resultados['metadatas'][0]
                    )
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
    area: Optional[str] = None
):
    """Lista todas las incidencias, con filtros opcionales"""
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
async def obtener_incidencia(incidencia_id: str):
    """Obtiene el detalle de una incidencia con todos sus reportes"""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener incidencia
    cursor.execute("SELECT * FROM incidencias WHERE id = ?", (incidencia_id,))
    incidencia = cursor.fetchone()
    
    if not incidencia:
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    
    # Obtener reportes asociados
    cursor.execute(
        "SELECT * FROM reportes WHERE incidencia_id = ? ORDER BY fecha",
        (incidencia_id,)
    )
    reportes = cursor.fetchall()
    conn.close()
    
    return {
        "incidencia": dict(incidencia),
        "reportes": [dict(r) for r in reportes]
    }

@app.post("/api/incidencias/{incidencia_id}/reportes")
async def agregar_reporte(incidencia_id: str, reporte: ReporteCreate):
    """
    Agrega un reporte de un participante a la incidencia.
    
    Múltiples personas pueden agregar su versión de los hechos.
    Cada reporte se guarda por separado para después consolidar.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar que existe la incidencia
    cursor.execute("SELECT id FROM incidencias WHERE id = ?", (incidencia_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    
    reporte_id = str(uuid.uuid4())
    ahora = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO reportes (id, incidencia_id, autor, contenido, fecha)
        VALUES (?, ?, ?, ?, ?)
    """, (reporte_id, incidencia_id, reporte.autor, reporte.contenido, ahora))
    
    # Actualizar fecha de la incidencia
    cursor.execute("""
        UPDATE incidencias SET fecha_actualizacion = ? WHERE id = ?
    """, (ahora, incidencia_id))
    
    conn.commit()
    conn.close()
    
    return {"id": reporte_id, "mensaje": "Reporte agregado"}

@app.post("/api/incidencias/{incidencia_id}/resolver")
async def resolver_incidencia(incidencia_id: str, solucion: SolucionCreate):
    """
    Marca una incidencia como resuelta y opcionalmente la agrega al RAG.
    
    Este es el momento clave donde el conocimiento se "hereda":
    - Se consolidan todos los reportes
    - Se genera un documento final
    - Se agrega a la base de conocimiento para futuros casos
    """
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener la incidencia completa
    cursor.execute("SELECT * FROM incidencias WHERE id = ?", (incidencia_id,))
    incidencia = cursor.fetchone()
    
    if not incidencia:
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    
    # Obtener todos los reportes
    cursor.execute(
        "SELECT * FROM reportes WHERE incidencia_id = ? ORDER BY fecha",
        (incidencia_id,)
    )
    reportes = cursor.fetchall()
    
    ahora = datetime.now().isoformat()
    
    # Actualizar incidencia
    cursor.execute("""
        UPDATE incidencias 
        SET estado = 'resuelto', solucion = ?, fecha_actualizacion = ?, agregado_a_rag = ?
        WHERE id = ?
    """, (solucion.solucion, ahora, 1 if solucion.agregar_a_rag else 0, incidencia_id))
    
    conn.commit()
    conn.close()
    
    # Si se debe agregar al RAG
    if solucion.agregar_a_rag and collection:
        # Construir documento completo
        reportes_texto = "\n".join([
            f"- {r['autor']}: {r['contenido']}"
            for r in reportes
        ])
        
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
        
        # Agregar al RAG
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
            return {
                "mensaje": "Incidencia resuelta pero error al agregar al RAG",
                "error": str(e)
            }
    
    return {"mensaje": "Incidencia resuelta y agregada a la base de conocimiento"}

@app.post("/api/incidencias/{incidencia_id}/generar-documento")
async def generar_documento_final(incidencia_id: str):
    """
    Usa el LLM para generar un documento consolidado.
    
    Este es el documento "oficial" que resume:
    - El problema
    - Los reportes de todos los involucrados
    - La solución aplicada
    - Lecciones aprendidas
    """
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener incidencia y reportes
    cursor.execute("SELECT * FROM incidencias WHERE id = ?", (incidencia_id,))
    incidencia = cursor.fetchone()
    
    if not incidencia:
        conn.close()
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    
    cursor.execute(
        "SELECT * FROM reportes WHERE incidencia_id = ? ORDER BY fecha",
        (incidencia_id,)
    )
    reportes = cursor.fetchall()
    conn.close()
    
    # Construir prompt para el LLM
    reportes_texto = "\n".join([
        f"Reporte de {r['autor']}:\n{r['contenido']}\n"
        for r in reportes
    ])
    
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

    # Consultar LLM
    documento_generado = await consultar_llm(prompt)
    
    return {
        "documento": documento_generado,
        "incidencia_id": incidencia_id
    }

# ============================================================
# ENDPOINTS - RAG (Base de Conocimiento)
# ============================================================

@app.post("/api/rag/consultar")
async def consultar_rag(consulta: ConsultaRAG):
    """
    Consulta la base de conocimiento y genera una respuesta con el LLM.
    
    Flujo:
    1. Busca documentos similares en ChromaDB (búsqueda semántica)
    2. Pasa esos documentos como contexto al LLM
    3. El LLM genera una respuesta informada
    """
    if not collection:
        raise HTTPException(status_code=500, detail="Base de conocimiento no inicializada")
    
    # Buscar en RAG
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
                    casos_encontrados.append({
                        "contenido": doc,
                        "metadata": meta
                    })
                    contexto += f"\n---\n{doc}\n"
        except Exception as e:
            print(f"Error buscando en RAG: {e}")
    
    # Generar respuesta con LLM
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
    tipo: str = Form("documento")
):
    """
    Agrega un documento a la base de conocimiento.
    
    Soporta archivos de texto (.txt, .md, .csv, etc.)
    El contenido se extrae y se guarda en ChromaDB.
    """
    if not collection:
        raise HTTPException(status_code=500, detail="Base de conocimiento no inicializada")
    
    # Leer contenido del archivo
    try:
        contenido = await archivo.read()
        texto = contenido.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error leyendo archivo: {e}")
    
    # Guardar archivo físico
    archivo_path = os.path.join(UPLOADS_DIR, archivo.filename)
    with open(archivo_path, 'wb') as f:
        f.write(contenido)
    
    # Generar ID único
    doc_id = str(uuid.uuid4())
    ahora = datetime.now().isoformat()
    
    # Guardar en SQLite
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documentos (id, nombre, tipo, fecha_subida, contenido_texto)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, titulo, tipo, ahora, texto[:10000]))  # Guardamos primeros 10k chars
    conn.commit()
    conn.close()
    
    # Agregar al RAG
    try:
        collection.add(
            documents=[texto],
            metadatas=[{
                "tipo": tipo,
                "titulo": titulo,
                "archivo": archivo.filename,
                "fecha": ahora
            }],
            ids=[f"doc_{doc_id}"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error agregando a RAG: {e}")
    
    return {
        "id": doc_id,
        "mensaje": "Documento agregado a la base de conocimiento",
        "total_documentos": collection.count()
    }

@app.get("/api/rag/documentos")
async def listar_documentos():
    """Lista todos los documentos en la base de conocimiento"""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, tipo, fecha_subida FROM documentos ORDER BY fecha_subida DESC")
    rows = cursor.fetchall()
    conn.close()
    
    # Obtener también incidencias agregadas al RAG
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titulo, area, fecha_creacion 
        FROM incidencias 
        WHERE agregado_a_rag = 1
        ORDER BY fecha_creacion DESC
    """)
    incidencias = cursor.fetchall()
    conn.close()
    
    return {
        "documentos": [dict(row) for row in rows],
        "incidencias_en_rag": [dict(i) for i in incidencias],
        "total": collection.count() if collection else 0
    }

@app.get("/api/rag/stats")
async def estadisticas_rag():
    """Estadísticas de la base de conocimiento"""
    return {
        "total_documentos": collection.count() if collection else 0,
        "estado": "activo" if collection else "inactivo"
    }

# ============================================================
# ENDPOINTS - CONFIGURACIÓN
# ============================================================

@app.get("/api/configuracion")
async def obtener_configuracion():
    """Obtiene la configuración actual del sistema"""
    return {
        "llm_provider": get_config("llm_provider") or "ollama",
        "llm_model": get_config("llm_model") or "llama3",
        "ollama_url": get_config("ollama_url") or "http://localhost:11434",
        "tiene_openai_key": bool(get_config("openai_api_key")),
        "tiene_anthropic_key": bool(get_config("anthropic_api_key"))
    }

@app.post("/api/configuracion")
async def actualizar_configuracion(config: ConfiguracionLLM):
    """Actualiza la configuración del LLM"""
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
async def probar_conexion_llm():
    """Prueba la conexión con el LLM configurado"""
    respuesta = await consultar_llm("Di 'Hola, estoy funcionando correctamente' y nada más.")
    return {
        "exito": "error" not in respuesta.lower(),
        "respuesta": respuesta
    }

# ============================================================
# ENDPOINT DE SALUD
# ============================================================

@app.get("/api/health")
async def health_check():
    """Verifica que el sistema está funcionando"""
    return {
        "estado": "ok",
        "base_datos": "ok",
        "rag": "ok" if collection else "no inicializado",
        "documentos_en_rag": collection.count() if collection else 0
    }

# ============================================================
# SERVIR FRONTEND
# ============================================================

# Ruta al frontend (se creará después)
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    
    @app.get("/")
    async def root():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
