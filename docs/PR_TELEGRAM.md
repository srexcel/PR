# PR_TELEGRAM: Integración Telegram

**Versión:** 1.0
**Prioridad:** P2 - ALTA
**Dependencias:** PR_CODIGO (P1), Python 3.10+

---

## 1. OBJETIVO

Canal alternativo a WhatsApp usando **Telegram Bot API**.

Ventajas sobre WhatsApp:
- API oficial y estable
- Sin riesgo de baneo
- Grupos con más funcionalidades
- Botones interactivos nativos

---

## 2. ARQUITECTURA

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Users                          │
│   📱 Operario    📱 Supervisor    📱 Admin                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ Telegram Bot API (HTTPS)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  TELEGRAM BOT SERVICE                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │   Polling   │ │   Handlers  │ │   Conversation      │   │
│  │   Updates   │ │   Commands  │ │   State Machine     │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PR-SYSTEM BACKEND                          │
│                    (FastAPI)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. ESTRUCTURA

```
PR/
├── main.py
├── pr_agent/
│
└── channels/
    └── telegram/
        ├── requirements.txt
        ├── config.py
        ├── bot.py              # Punto de entrada
        ├── handlers/
        │   ├── __init__.py
        │   ├── start.py        # /start, /help
        │   ├── problema.py     # Flujo de problemas
        │   ├── buscar.py       # Búsqueda RAG
        │   └── admin.py        # Comandos admin
        ├── services/
        │   ├── __init__.py
        │   └── pr_api.py       # Cliente API
        └── utils/
            ├── __init__.py
            └── keyboards.py    # Teclados inline
```

---

## 4. IMPLEMENTACIÓN

### 4.1 requirements.txt

```
python-telegram-bot==20.7
httpx==0.27.0
python-dotenv==1.0.0
```

### 4.2 config.py

```python
# channels/telegram/config.py

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")

# PR-System API
PR_API_URL = os.getenv("PR_API_URL", "http://localhost:8000")
PR_API_USER = os.getenv("PR_API_USER", "telegram_bot")
PR_API_PASS = os.getenv("PR_API_PASS")

# Estados de conversación
(
    ESTADO_IDLE,
    ESTADO_DESCRIPCION,
    ESTADO_AREA,
    ESTADO_CONFIRMANDO,
    ESTADO_DOCUMENTANDO,
) = range(5)
```

### 4.3 bot.py (Punto de entrada)

```python
# channels/telegram/bot.py

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from config import TELEGRAM_TOKEN, ESTADO_IDLE, ESTADO_DESCRIPCION, ESTADO_AREA, ESTADO_CONFIRMANDO, ESTADO_DOCUMENTANDO
from handlers.start import start, help_command, cancel
from handlers.problema import (
    problema_inicio,
    problema_descripcion,
    problema_area,
    problema_confirmacion,
    problema_documentacion,
)
from handlers.buscar import buscar_comando, buscar_texto
from handlers.admin import stats_comando

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Inicia el bot"""

    # Crear aplicación
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation handler para flujo de problemas
    problema_conv = ConversationHandler(
        entry_points=[
            CommandHandler("problema", problema_inicio),
            MessageHandler(
                filters.Regex(r"(?i)(problema|falla|error|ayuda|no funciona)"),
                problema_inicio
            ),
        ],
        states={
            ESTADO_DESCRIPCION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, problema_descripcion)
            ],
            ESTADO_AREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, problema_area),
                CallbackQueryHandler(problema_area, pattern=r"^area_"),
            ],
            ESTADO_CONFIRMANDO: [
                CallbackQueryHandler(problema_confirmacion, pattern=r"^caso_"),
            ],
            ESTADO_DOCUMENTANDO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, problema_documentacion),
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cancel),
            CommandHandler("cancel", cancel),
        ],
    )

    # Registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ayuda", help_command))
    app.add_handler(CommandHandler("buscar", buscar_comando))
    app.add_handler(CommandHandler("stats", stats_comando))
    app.add_handler(problema_conv)

    # Handler genérico para búsquedas
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        buscar_texto
    ))

    # Iniciar
    logger.info("Bot PR-System iniciando...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
```

### 4.4 handlers/start.py

```python
# channels/telegram/handlers/start.py

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import ESTADO_IDLE


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""

    mensaje = """🤖 *PR-System Bot*

Bienvenido al Sistema de Conocimiento Vivo.

*Comandos disponibles:*

📋 /problema - Reportar un nuevo problema
🔍 /buscar `<texto>` - Buscar en base de conocimiento
📊 /stats - Ver estadísticas
❓ /ayuda - Mostrar ayuda
❌ /cancelar - Cancelar operación

_"¿Qué aprendimos la última vez que pasó esto?"_
"""

    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help o /ayuda"""

    mensaje = """📚 *Guía de Uso PR-System*

*1. Reportar un Problema*
Escribe /problema o simplemente describe tu problema.
El sistema buscará casos similares automáticamente.

*2. Buscar Soluciones*
Usa /buscar seguido de palabras clave.
Ejemplo: `/buscar soldadura porosidad`

*3. Ver Estadísticas*
Usa /stats para ver el estado del sistema.

*Flujo PR:*
1️⃣ Reportas problema
2️⃣ Sistema busca casos similares
3️⃣ Si existe solución → Te la muestra
4️⃣ Si es nuevo → Documenta para el futuro

_Cada caso resuelto alimenta la base de conocimiento._
"""

    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la conversación actual"""

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Operación cancelada.\n\n¿En qué puedo ayudarte?",
        parse_mode="Markdown"
    )

    return ConversationHandler.END
```

### 4.5 handlers/problema.py

```python
# channels/telegram/handlers/problema.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    ESTADO_DESCRIPCION,
    ESTADO_AREA,
    ESTADO_CONFIRMANDO,
    ESTADO_DOCUMENTANDO,
)
from services.pr_api import PRApiClient
from utils.keyboards import crear_teclado_areas, crear_teclado_confirmacion

api = PRApiClient()


async def problema_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de reporte de problema"""

    mensaje = """📋 *Nuevo Reporte PR*

Describe el problema con el mayor detalle posible:

• ¿Qué está pasando?
• ¿Cuándo empezó?
• ¿Qué equipo o área está afectada?

_Escribe /cancelar para salir_"""

    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown"
    )

    return ESTADO_DESCRIPCION


async def problema_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la descripción del problema"""

    descripcion = update.message.text

    if len(descripcion) < 10:
        await update.message.reply_text(
            "⚠️ La descripción es muy corta. Por favor, proporciona más detalles."
        )
        return ESTADO_DESCRIPCION

    # Guardar en contexto
    context.user_data["descripcion"] = descripcion

    # Mostrar selector de área
    mensaje = "📍 *¿En qué área ocurre el problema?*"

    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=crear_teclado_areas()
    )

    return ESTADO_AREA


async def problema_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el área y busca casos similares"""

    # Determinar área desde botón o texto
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        area = query.data.replace("area_", "")
        mensaje_obj = query.message
    else:
        area = update.message.text
        mensaje_obj = update.message

    context.user_data["area"] = area

    # Notificar búsqueda
    await mensaje_obj.reply_text("🔍 Buscando casos similares...")

    # Llamar a API PR-System
    try:
        resultado = await api.reportar_problema(
            descripcion=context.user_data["descripcion"],
            area=area,
            usuario=str(update.effective_user.id)
        )

        context.user_data["resultado"] = resultado

        # Verificar si hay casos similares
        if resultado.get("casos_similares"):
            casos = resultado["casos_similares"]

            mensaje = f"🔍 *Encontré {len(casos)} caso(s) similar(es):*\n\n"

            for i, caso in enumerate(casos[:3], 1):
                mensaje += f"*{i}. {caso.get('version', 'Caso')}*\n"
                mensaje += f"   📅 {caso.get('fecha', 'N/A')}\n"
                mensaje += f"   📝 {caso.get('resumen', '')[:100]}...\n\n"

            mensaje += "_¿Alguno de estos casos aplica a tu situación?_"

            await mensaje_obj.reply_text(
                mensaje,
                parse_mode="Markdown",
                reply_markup=crear_teclado_confirmacion()
            )

            return ESTADO_CONFIRMANDO

        else:
            # Es un caso nuevo
            context.user_data["incidencia_id"] = resultado.get("incidencia_id")

            mensaje = """📝 *Caso Nuevo Registrado*

No encontré casos similares. Esto se documentará para el futuro.

Por favor, proporciona información adicional:
• ¿Qué has intentado?
• ¿Quién más está involucrado?
• ¿Qué impacto tiene?"""

            await mensaje_obj.reply_text(
                mensaje,
                parse_mode="Markdown"
            )

            return ESTADO_DOCUMENTANDO

    except Exception as e:
        await mensaje_obj.reply_text(
            f"❌ Error consultando el sistema: {str(e)}"
        )
        return ConversationHandler.END


async def problema_confirmacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la confirmación de caso similar"""

    query = update.callback_query
    await query.answer()

    accion = query.data

    if accion == "caso_si":
        # Mostrar detalle del caso más relevante
        casos = context.user_data.get("resultado", {}).get("casos_similares", [])

        if casos:
            caso = casos[0]

            mensaje = f"""✅ *Caso Similar Encontrado*

*{caso.get('version', 'Caso')}*

{caso.get('contenido', caso.get('resumen', 'Sin contenido'))}

---
_Si esto resolvió tu problema, no necesitas hacer nada más._
_Si necesitas reportar algo diferente, usa /problema nuevamente._"""

            await query.message.reply_text(
                mensaje,
                parse_mode="Markdown"
            )

        context.user_data.clear()
        return ConversationHandler.END

    elif accion == "caso_no":
        # Crear caso nuevo
        context.user_data["incidencia_id"] = context.user_data.get("resultado", {}).get("incidencia_id")

        mensaje = """📝 *Creando Caso Nuevo*

Entendido, tu situación es diferente.

Por favor, describe qué hace diferente a tu caso:"""

        await query.message.reply_text(
            mensaje,
            parse_mode="Markdown"
        )

        return ESTADO_DOCUMENTANDO

    return ESTADO_CONFIRMANDO


async def problema_documentacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe documentación adicional"""

    texto = update.message.text
    incidencia_id = context.user_data.get("incidencia_id")

    if incidencia_id:
        try:
            await api.agregar_reporte(
                incidencia_id=incidencia_id,
                contenido=texto,
                autor=str(update.effective_user.id)
            )
        except Exception as e:
            print(f"Error agregando reporte: {e}")

    mensaje = f"""✅ *Información Registrada*

Tu reporte ha sido documentado.

📌 ID: `{incidencia_id[:8] if incidencia_id else 'N/A'}...`

Un supervisor revisará el caso y documentará la solución.
Cuando se resuelva, quedará en la base de conocimiento.

_Escribe /problema si tienes otro tema._"""

    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown"
    )

    context.user_data.clear()
    return ConversationHandler.END
```

### 4.6 handlers/buscar.py

```python
# channels/telegram/handlers/buscar.py

from telegram import Update
from telegram.ext import ContextTypes

from services.pr_api import PRApiClient

api = PRApiClient()


async def buscar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /buscar <texto>"""

    if not context.args:
        await update.message.reply_text(
            "🔍 Uso: /buscar `<palabras clave>`\n\n"
            "Ejemplo: `/buscar soldadura porosidad`",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args)
    await realizar_busqueda(update, query)


async def buscar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Búsqueda desde texto libre (fallback)"""

    texto = update.message.text

    # Solo buscar si parece una pregunta o consulta
    if any(palabra in texto.lower() for palabra in ["?", "cómo", "como", "qué", "que", "dónde", "donde", "por qué"]):
        await realizar_busqueda(update, texto)


async def realizar_busqueda(update: Update, query: str):
    """Realiza la búsqueda en RAG"""

    await update.message.reply_text("🔍 Buscando...")

    try:
        resultado = await api.consultar_rag(query)

        casos = resultado.get("casos_similares", [])

        if not casos:
            await update.message.reply_text(
                f"🔍 No encontré casos relacionados con \"{query}\".\n\n"
                "¿Quieres reportar un problema? Usa /problema"
            )
            return

        mensaje = f"🔍 *Resultados para \"{query}\":*\n\n"

        for i, caso in enumerate(casos[:3], 1):
            titulo = caso.get("metadata", {}).get("titulo", "Caso")
            contenido = caso.get("contenido", "")[:200]

            mensaje += f"*{i}. {titulo}*\n"
            mensaje += f"{contenido}...\n\n"

        # Agregar respuesta del LLM si existe
        if resultado.get("respuesta"):
            mensaje += f"---\n💡 *Resumen:*\n{resultado['respuesta']}"

        await update.message.reply_text(
            mensaje,
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error en la búsqueda: {str(e)}"
        )
```

### 4.7 utils/keyboards.py

```python
# channels/telegram/utils/keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def crear_teclado_areas():
    """Crea teclado inline para selección de área"""

    keyboard = [
        [
            InlineKeyboardButton("🏭 Producción", callback_data="area_Produccion"),
            InlineKeyboardButton("✅ Calidad", callback_data="area_Calidad"),
        ],
        [
            InlineKeyboardButton("🔧 Mantenimiento", callback_data="area_Mantenimiento"),
            InlineKeyboardButton("📦 Logística", callback_data="area_Logistica"),
        ],
        [
            InlineKeyboardButton("⚙️ Ingeniería", callback_data="area_Ingenieria"),
            InlineKeyboardButton("📝 Otra", callback_data="area_Otra"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def crear_teclado_confirmacion():
    """Crea teclado para confirmar caso similar"""

    keyboard = [
        [
            InlineKeyboardButton("✅ Sí, me sirve", callback_data="caso_si"),
            InlineKeyboardButton("❌ No, es diferente", callback_data="caso_no"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def crear_teclado_prioridad():
    """Crea teclado para selección de prioridad"""

    keyboard = [
        [
            InlineKeyboardButton("🟢 Baja", callback_data="prioridad_baja"),
            InlineKeyboardButton("🟡 Media", callback_data="prioridad_media"),
        ],
        [
            InlineKeyboardButton("🟠 Alta", callback_data="prioridad_alta"),
            InlineKeyboardButton("🔴 Crítica", callback_data="prioridad_critica"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)
```

### 4.8 services/pr_api.py

```python
# channels/telegram/services/pr_api.py

import httpx
from config import PR_API_URL, PR_API_USER, PR_API_PASS


class PRApiClient:
    """Cliente para API de PR-System"""

    def __init__(self):
        self.base_url = PR_API_URL
        self.token = None

    async def _authenticate(self):
        """Obtiene token JWT"""

        if self.token:
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                data={
                    "username": PR_API_USER,
                    "password": PR_API_PASS,
                }
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]

    async def _request(self, method: str, endpoint: str, **kwargs):
        """Realiza request autenticado"""

        await self._authenticate()

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30.0,
                **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def reportar_problema(self, descripcion: str, area: str, usuario: str):
        """Reporta un problema al sistema PR"""

        return await self._request(
            "POST",
            "/api/pr/problema",
            data={
                "descripcion": descripcion,
                "area": area,
            }
        )

    async def agregar_reporte(self, incidencia_id: str, contenido: str, autor: str):
        """Agrega reporte a una incidencia"""

        return await self._request(
            "POST",
            f"/api/incidencias/{incidencia_id}/reportes",
            json={
                "autor": autor,
                "contenido": contenido,
            }
        )

    async def consultar_rag(self, pregunta: str):
        """Consulta la base de conocimiento"""

        return await self._request(
            "POST",
            "/api/rag/consultar",
            json={
                "pregunta": pregunta,
                "n_resultados": 5,
            }
        )

    async def obtener_stats(self):
        """Obtiene estadísticas del sistema"""

        return await self._request("GET", "/api/rag/stats")
```

---

## 5. CREAR BOT EN TELEGRAM

1. Abrir @BotFather en Telegram
2. Enviar `/newbot`
3. Elegir nombre: `PR-System Bot`
4. Elegir username: `pr_system_bot` (debe terminar en `bot`)
5. Copiar el token

---

## 6. INSTALACIÓN

```bash
# 1. Ir al directorio
cd PR/channels/telegram

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar .env
echo "TELEGRAM_TOKEN=tu_token_aqui" > .env
echo "PR_API_URL=http://localhost:8000" >> .env
echo "PR_API_USER=telegram_bot" >> .env
echo "PR_API_PASS=tu_password" >> .env

# 5. Iniciar
python bot.py
```

---

## 7. CHECKLIST

- [ ] Crear bot en @BotFather
- [ ] Crear estructura `channels/telegram/`
- [ ] Implementar `bot.py`
- [ ] Implementar handlers
- [ ] Implementar `pr_api.py`
- [ ] Crear usuario bot en PR-System
- [ ] Configurar `.env`
- [ ] Probar comandos básicos
- [ ] Probar flujo completo de problema

---

*Este documento es checkpoint v1.0 de PR_TELEGRAM*
*v1.1 viene después del siguiente error*
