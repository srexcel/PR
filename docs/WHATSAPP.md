# 📱 PR-System: Integración WhatsApp

> **Documentar problemas desde WhatsApp. Sin apps nuevas. Sin capacitación.**

---

## 📋 Índice

1. [Objetivo](#-objetivo)
2. [¿Por qué WhatsApp?](#-por-qué-whatsapp)
3. [Arquitectura](#-arquitectura)
4. [Flujo de Conversación](#-flujo-de-conversación)
5. [Comandos del Bot](#-comandos-del-bot)
6. [Requisitos](#-requisitos)
7. [Instalación](#-instalación)
8. [Configuración](#-configuración)
9. [Estructura del Código](#-estructura-del-código)
10. [API de Integración](#-api-de-integración)
11. [Seguridad](#-seguridad)
12. [Casos de Uso](#-casos-de-uso)
13. [Solución de Problemas](#-solución-de-problemas)
14. [Roadmap](#-roadmap)

---

## 🎯 Objetivo

### El Problema

```
SITUACIÓN ACTUAL EN PLANTAS INDUSTRIALES:
──────────────────────────────────────────

1. Operador detecta problema
2. Busca al supervisor (no está disponible)
3. Intenta resolver solo "como pueda"
4. Si funciona → No se documenta
5. Si no funciona → Llama a mantenimiento
6. Se resuelve → Nadie documenta la solución
7. Próxima semana → Mismo problema, empezar de cero

RESULTADO:
• 90% de casos no se documentan
• Conocimiento en la cabeza de 2-3 personas
• Cuando renuncian, el conocimiento se va
• Problemas recurrentes sin solución definitiva
```

### La Solución

```
CON PR-SYSTEM + WHATSAPP:
─────────────────────────

1. Operador detecta problema
2. Manda WhatsApp: "Hay porosidad en soldadura"
3. Bot responde: "Encontré 2 casos similares..."
4. Operador aplica solución sugerida
5. Confirma: "Ya quedó"
6. Bot documenta automáticamente
7. Próxima vez → El sistema ya sabe qué hacer

RESULTADO:
• 95% de casos documentados (es más fácil que NO hacerlo)
• Conocimiento en el sistema, no en personas
• Respuesta inmediata con soluciones probadas
• Mejora continua automática
```

---

## 💡 ¿Por qué WhatsApp?

### Comparativa de Canales

| Canal | Adopción | Capacitación | Multimedia | Ubicuidad | Costo |
|-------|----------|--------------|------------|-----------|-------|
| **WhatsApp** | ✅ 95%+ | ✅ Ninguna | ✅ Fotos/Video | ✅ Total | ✅ Gratis |
| App Custom | ❌ 0% | ❌ Alta | ✅ Sí | ⚠️ Parcial | ❌ Alto |
| Email | ⚠️ 60% | ⚠️ Media | ✅ Sí | ⚠️ Parcial | ✅ Gratis |
| Portal Web | ❌ 20% | ❌ Alta | ✅ Sí | ❌ Solo PC | ⚠️ Medio |
| Llamada | ✅ 100% | ✅ Ninguna | ❌ No | ✅ Total | ⚠️ Medio |

### Ventajas Específicas

| Ventaja | Descripción |
|---------|-------------|
| **Cero fricción** | No hay app que instalar, ya tienen WhatsApp |
| **Fotos inmediatas** | "Mira cómo está la pieza" → Diagnóstico visual |
| **Voz a texto** | Pueden dictar en lugar de escribir |
| **Notificaciones** | El bot puede alertar de problemas críticos |
| **Grupos** | Notificar a todo el equipo de mantenimiento |
| **Histórico** | Conversación queda como registro |
| **24/7** | El bot siempre está disponible |

---

## 🏗️ Arquitectura

### Diagrama General

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARQUITECTURA                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │   Usuario    │                                               │
│  │  (WhatsApp)  │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         │ WebSocket                                              │
│         ▼                                                        │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   WhatsApp   │     │   Baileys    │     │   PR-Bot     │    │
│  │   Servers    │◀───▶│   (Bridge)   │◀───▶│   (Node.js)  │    │
│  └──────────────┘     └──────────────┘     └──────┬───────┘    │
│                                                    │             │
│                                              HTTP REST           │
│                                                    │             │
│                                                    ▼             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     PR-SYSTEM API                        │   │
│  │                      (FastAPI)                           │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │
│  │  │  PR-Agent  │  │  ChromaDB  │  │   Ollama   │        │   │
│  │  │   (Ciclo)  │  │   (RAG)    │  │   (LLM)    │        │   │
│  │  └────────────┘  └────────────┘  └────────────┘        │   │
│  │                                                          │   │
│  │  ┌────────────┐  ┌────────────┐                         │   │
│  │  │  SQLite    │  │  Versiones │                         │   │
│  │  │   (Data)   │  │  (v1.0...) │                         │   │
│  │  └────────────┘  └────────────┘                         │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Componentes

| Componente | Tecnología | Función |
|------------|------------|---------|
| **Baileys** | Node.js | Conexión con WhatsApp Web |
| **PR-Bot** | Node.js/TypeScript | Lógica del bot, manejo de sesiones |
| **PR-System API** | FastAPI (Python) | Backend principal |
| **ChromaDB** | Vector DB | Búsqueda semántica de casos |
| **Ollama** | LLM Local | Procesamiento de lenguaje natural |
| **SQLite** | Database | Datos de usuarios, sesiones, casos |

### Flujo de Datos

```
1. Usuario envía mensaje a WhatsApp
         │
         ▼
2. WhatsApp Servers reciben mensaje
         │
         ▼
3. Baileys (conectado como WhatsApp Web) recibe evento
         │
         ▼
4. PR-Bot procesa mensaje:
   ├── Identifica usuario (número de teléfono)
   ├── Obtiene contexto de conversación
   ├── Detecta intención (problema, consulta, respuesta)
   │
   ▼
5. PR-Bot llama a PR-System API:
   ├── POST /api/pr/problema (si es nuevo problema)
   ├── POST /api/pr/consultar (si es consulta)
   ├── POST /api/pr/resolver (si cierra caso)
   │
   ▼
6. PR-System procesa:
   ├── Busca casos similares (RAG)
   ├── Genera respuesta (LLM)
   ├── Actualiza base de datos
   │
   ▼
7. PR-Bot recibe respuesta
         │
         ▼
8. Baileys envía mensaje de vuelta
         │
         ▼
9. Usuario recibe respuesta en WhatsApp
```

---

## 💬 Flujo de Conversación

### Caso 1: Problema Nuevo (Sin casos similares)

```
👷 Operador:
"Hola, tenemos un problema con la inyectora 5,
está haciendo piezas con rebaba"

🤖 Bot:
Hola Juan! Registré tu problema:
📋 *Problema:* Rebaba en inyectora 5
🏭 *Área:* Producción (detectada automáticamente)
⚠️ *Prioridad:* Media

No encontré casos similares previos.
Este parece ser un caso nuevo.

Para documentarlo mejor, ¿podrías decirme:
1. ¿Cuándo empezó el problema?
2. ¿En qué molde/producto ocurre?
3. ¿Ya intentaron algo?

👷 Operador:
"Empezó hace como 2 horas, es en el molde del
contenedor azul, ya le bajamos temperatura pero sigue"

🤖 Bot:
Entendido. Actualicé el caso:
• Inicio: hace 2 horas
• Molde: contenedor azul
• Intentado: bajar temperatura (sin éxito)

¿Quieres que notifique a mantenimiento o
prefieres seguir investigando?

👷 Operador:
"Avísales porfa"

🤖 Bot:
✅ Notifiqué al grupo de Mantenimiento.
Tu caso es el #INY-2024-0847

Te aviso cuando respondan.
```

### Caso 2: Problema con Casos Similares

```
👷 Operador:
"Hay porosidad en las soldaduras de la línea 3"

🤖 Bot:
Hola María! Encontré *2 casos similares*:

📁 *SOLDADURA_v1.0* (hace 3 meses)
   Problema: Porosidad por electrodos desgastados
   Solución: Cambiar electrodos cada 500 ciclos
   ✅ Funcionó

📁 *SOLDADURA_v1.1* (hace 2 semanas)
   Problema: Porosidad por humedad en gas CO2
   Solución: Purgar líneas de gas, revisar tanque
   ✅ Funcionó

¿Alguno de estos aplica a tu caso?

👷 Operador:
"Creo que es el segundo, el tanque se ve húmedo"

🤖 Bot:
Perfecto. Según SOLDADURA_v1.1, la solución es:

1. Purgar las líneas de gas (5 minutos)
2. Revisar válvula del tanque CO2
3. Si hay condensación, cambiar tanque

¿Necesitas que te envíe el procedimiento
detallado o ya sabes cómo hacerlo?

👷 Operador:
"Ya sé, déjame intentar"

🤖 Bot:
Ok! Te marco el caso como "en proceso".
Avísame cuando termines para cerrar el ciclo.

--- 30 minutos después ---

👷 Operador:
"Ya quedó, era el tanque"

🤖 Bot:
¡Excelente! 🎉

Caso cerrado. Creé nueva versión:
📁 *SOLDADURA_v1.2*
   Problema: Porosidad por humedad en tanque CO2
   Solución: Cambio de tanque
   Tiempo: 30 minutos

¿Algo más que agregar para futuros casos?

👷 Operador:
"Sí, el tanque estaba en el sol, hay que moverlos a la sombra"

🤖 Bot:
✅ Agregado como acción preventiva:
"Almacenar tanques CO2 en área sombreada"

Gracias María! El conocimiento quedó guardado.
```

### Caso 3: Envío de Foto

```
👷 Operador:
📷 [Envía foto de pieza defectuosa]
"Mira cómo está saliendo"

🤖 Bot:
Recibí la foto. La guardé como evidencia.

Por lo que veo, parece un problema de:
• Posible falta de material
• O temperatura incorrecta

¿Puedes confirmar qué máquina/proceso es?

👷 Operador:
"Es la troqueladora 2"

🤖 Bot:
Encontré 1 caso similar:

📁 *TROQUELADO_v2.3*
   Problema: Piezas incompletas
   Causa: Presión de aire baja
   Solución: Revisar compresor, filtro de aire

¿Quieres que registre esto como nuevo caso
o es el mismo problema de antes?
```

### Caso 4: Consulta de Conocimiento

```
👷 Supervisor:
"¿Qué problemas hemos tenido con la CNC-05?"

🤖 Bot:
Encontré *4 casos* de CNC-05:

1. *CNC05_v1.0* (Ene 2024)
   Vibración excesiva → Cambio de rodamiento

2. *CNC05_v1.1* (Mar 2024)
   Error de posición → Recalibrar encoder

3. *CNC05_v1.2* (Jun 2024)
   Sobrecalentamiento → Limpiar filtro de aceite

4. *CNC05_v2.0* (Oct 2024)
   Falla total → Cambio de tarjeta controladora

¿Quieres ver el detalle de alguno?

👷 Supervisor:
"El de vibración"

🤖 Bot:
📁 *CNC05_v1.0* - Vibración Excesiva

*Síntomas:*
- Ruido anormal en eje Y
- Acabado superficial deficiente
- Vibración perceptible al tacto

*Diagnóstico:*
- Rodamiento del husillo eje Y desgastado

*Solución:*
- Cambio de rodamiento SKF 7210
- Lubricación con grasa Kluber

*Tiempo de reparación:* 4 horas
*Costo:* $2,500 MXN
*Técnico:* Roberto Sánchez

*Acciones preventivas:*
- Revisar vibración cada 500 horas
- Lubricar cada 200 horas
```

---

## ⌨️ Comandos del Bot

### Comandos Principales

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/problema` | Reportar nuevo problema | `/problema Fuga de aceite en prensa 3` |
| `/buscar` | Buscar casos similares | `/buscar soldadura porosidad` |
| `/resolver` | Cerrar caso activo | `/resolver Cambié el filtro, funcionó` |
| `/estado` | Ver mis casos abiertos | `/estado` |
| `/historial` | Ver casos cerrados | `/historial` |
| `/ayuda` | Lista de comandos | `/ayuda` |

### Comandos de Supervisor

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/casos` | Ver todos los casos abiertos | `/casos` |
| `/area` | Filtrar por área | `/area mantenimiento` |
| `/asignar` | Asignar caso a técnico | `/asignar #123 a Roberto` |
| `/stats` | Estadísticas del sistema | `/stats` |
| `/exportar` | Exportar reporte | `/exportar semana` |

### Lenguaje Natural

El bot también entiende lenguaje natural:

```
✅ "Tenemos un problema con la máquina 5"
✅ "¿Qué casos de soldadura hay?"
✅ "Ya lo arreglé, era el filtro"
✅ "Avísale a mantenimiento"
✅ "¿Cómo se resolvió lo de la banda?"
```

---

## 📋 Requisitos

### Hardware

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| **Servidor** | 2 CPU, 4GB RAM | 4 CPU, 8GB RAM |
| **Almacenamiento** | 20GB SSD | 50GB SSD |
| **Red** | 10 Mbps | 100 Mbps |
| **Teléfono** | Cualquier Android/iOS | Android dedicado |

### Software

| Software | Versión | Notas |
|----------|---------|-------|
| **Node.js** | 18+ | Para Baileys |
| **Python** | 3.10+ | Para PR-System |
| **Ollama** | Latest | LLM local |
| **PM2** | Latest | Process manager |
| **Git** | Latest | Control de versiones |

### Cuenta WhatsApp

- Número de teléfono dedicado (no usar personal)
- SIM activa (puede ser prepago)
- WhatsApp instalado en teléfono físico o emulador
- Cuenta verificada

---

## 🛠️ Instalación

### Paso 1: Clonar Repositorio

```bash
git clone https://github.com/srexcel/PR.git
cd PR
```

### Paso 2: Instalar PR-System (si no está instalado)

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o: .\venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```

### Paso 3: Instalar WhatsApp Bot

```bash
# Ir a directorio del bot
cd whatsapp-bot

# Instalar dependencias Node.js
npm install

# Copiar configuración
cp .env.example .env
```

### Paso 4: Configurar Variables de Entorno

Editar `.env`:

```env
# PR-System API
PR_API_URL=http://localhost:8000
PR_API_USER=whatsapp-bot
PR_API_PASSWORD=secure-password-here

# WhatsApp
WHATSAPP_SESSION_NAME=pr-system-bot

# Configuración
BOT_PREFIX=/
ADMIN_NUMBERS=5215512345678,5215587654321
DEFAULT_AREA=Producción
LOG_LEVEL=info

# Base de datos de sesiones
SESSION_DB_PATH=./data/sessions.db
```

### Paso 5: Vincular WhatsApp

```bash
# Iniciar bot (primera vez)
npm start

# Aparecerá código QR en terminal
# Escanear con WhatsApp del teléfono dedicado:
# WhatsApp → Configuración → Dispositivos vinculados → Vincular
```

### Paso 6: Iniciar Servicios

```bash
# Terminal 1: PR-System API
cd /ruta/a/PR
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Ollama
ollama serve

# Terminal 3: WhatsApp Bot
cd /ruta/a/PR/whatsapp-bot
npm start
```

### Paso 7: Configurar como Servicio (Producción)

```bash
# Instalar PM2
npm install -g pm2

# Iniciar servicios
pm2 start ecosystem.config.js

# Guardar configuración
pm2 save

# Configurar inicio automático
pm2 startup
```

---

## ⚙️ Configuración

### Archivo de Configuración Principal

`whatsapp-bot/config/config.js`:

```javascript
module.exports = {
  // Conexión con PR-System
  prSystem: {
    apiUrl: process.env.PR_API_URL || 'http://localhost:8000',
    apiUser: process.env.PR_API_USER,
    apiPassword: process.env.PR_API_PASSWORD,
    timeout: 30000
  },

  // Configuración del bot
  bot: {
    prefix: '/',
    sessionName: process.env.WHATSAPP_SESSION_NAME || 'pr-bot',
    defaultArea: process.env.DEFAULT_AREA || 'Producción',
    language: 'es'
  },

  // Administradores
  admins: (process.env.ADMIN_NUMBERS || '').split(','),

  // Áreas válidas
  areas: [
    'Producción',
    'Mantenimiento',
    'Calidad',
    'Logística',
    'Ingeniería'
  ],

  // Prioridades
  priorities: {
    alta: { emoji: '🔴', timeout: 30 },    // 30 min para responder
    media: { emoji: '🟡', timeout: 120 },   // 2 horas
    baja: { emoji: '🟢', timeout: 480 }     // 8 horas
  },

  // Mensajes
  messages: {
    welcome: '¡Hola! Soy el asistente de PR-System. ¿En qué puedo ayudarte?',
    unknownCommand: 'No entendí ese comando. Escribe /ayuda para ver opciones.',
    error: 'Hubo un error procesando tu mensaje. Intenta de nuevo.',
    casoCerrado: '✅ Caso cerrado. ¡Gracias por documentar!'
  },

  // Grupos autorizados (opcional)
  authorizedGroups: [
    // 'ID_DEL_GRUPO_1',
    // 'ID_DEL_GRUPO_2'
  ],

  // Logs
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: './logs/bot.log'
  }
};
```

### Configurar Usuarios

`whatsapp-bot/config/users.js`:

```javascript
// Mapeo de números a usuarios del sistema
module.exports = {
  '5215512345678': {
    nombre: 'Juan Pérez',
    area: 'Producción',
    rol: 'operador',
    prUserId: 'uuid-del-usuario-en-pr-system'
  },
  '5215587654321': {
    nombre: 'María García',
    area: 'Mantenimiento',
    rol: 'supervisor',
    prUserId: 'uuid-del-usuario-en-pr-system'
  }
  // Agregar más usuarios...
};
```

### Configurar Notificaciones de Grupo

```javascript
// whatsapp-bot/config/notifications.js
module.exports = {
  // Cuando se crea caso de alta prioridad
  altaPrioridad: {
    notificar: true,
    grupos: ['ID_GRUPO_SUPERVISORES'],
    mensaje: '🔴 *URGENTE* Nuevo caso de alta prioridad:\n{descripcion}\nReportado por: {usuario}'
  },

  // Cuando un caso lleva mucho tiempo abierto
  casoAtrasado: {
    notificar: true,
    grupos: ['ID_GRUPO_SUPERVISORES'],
    mensaje: '⚠️ Caso #{id} lleva {tiempo} sin resolverse'
  },

  // Resumen diario
  resumenDiario: {
    enabled: true,
    hora: '18:00',
    grupos: ['ID_GRUPO_GERENCIA'],
    mensaje: '📊 *Resumen del día*\nCasos nuevos: {nuevos}\nResueltos: {resueltos}\nPendientes: {pendientes}'
  }
};
```

---

## 📁 Estructura del Código

```
whatsapp-bot/
├── src/
│   ├── index.js              # Punto de entrada
│   ├── bot.js                # Clase principal del bot
│   ├── connection.js         # Conexión con Baileys
│   │
│   ├── handlers/             # Manejadores de mensajes
│   │   ├── messageHandler.js # Router principal
│   │   ├── commandHandler.js # Procesa /comandos
│   │   ├── naturalHandler.js # Procesa lenguaje natural
│   │   └── mediaHandler.js   # Procesa fotos/videos
│   │
│   ├── services/             # Servicios
│   │   ├── prSystemService.js    # Conexión con PR-API
│   │   ├── sessionService.js     # Manejo de sesiones
│   │   ├── notificationService.js # Notificaciones
│   │   └── nlpService.js         # Detección de intención
│   │
│   ├── commands/             # Comandos disponibles
│   │   ├── problema.js       # /problema
│   │   ├── buscar.js         # /buscar
│   │   ├── resolver.js       # /resolver
│   │   ├── estado.js         # /estado
│   │   └── ayuda.js          # /ayuda
│   │
│   ├── utils/                # Utilidades
│   │   ├── formatter.js      # Formatear mensajes
│   │   ├── validator.js      # Validar inputs
│   │   └── logger.js         # Logging
│   │
│   └── models/               # Modelos de datos
│       ├── Session.js        # Sesión de usuario
│       └── Conversation.js   # Estado de conversación
│
├── config/
│   ├── config.js             # Configuración principal
│   ├── users.js              # Mapeo de usuarios
│   └── notifications.js      # Config de notificaciones
│
├── data/
│   ├── sessions/             # Sesiones de WhatsApp
│   └── sessions.db           # SQLite de sesiones
│
├── logs/
│   └── bot.log               # Logs del bot
│
├── package.json
├── ecosystem.config.js       # Config de PM2
└── .env.example
```

---

## 🔌 API de Integración

### Endpoints que usa el Bot

#### Reportar Problema

```javascript
// POST /api/pr/problema
const response = await fetch(`${PR_API_URL}/api/pr/problema`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    descripcion: 'Fuga de aceite en prensa hidráulica 3',
    area: 'Mantenimiento',
    prioridad: 'alta',
    metadata: {
      canal: 'whatsapp',
      telefono: '5215512345678',
      nombre: 'Juan Pérez'
    }
  })
});

// Respuesta
{
  "fase": "DURANTE",
  "pregunta": "¿Cómo falla?",
  "checkpoint_id": "uuid",
  "incidencia_id": "uuid",
  "es_caso_nuevo": false,
  "casos_similares": [...],
  "preguntas_guia": [...]
}
```

#### Resolver Caso

```javascript
// POST /api/pr/resolver/{incidencia_id}
const response = await fetch(`${PR_API_URL}/api/pr/resolver/${incidenciaId}`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    solucion: 'Se cambió el sello hidráulico',
    causa_raiz: 'Sello desgastado por uso',
    acciones_preventivas: 'Revisar sellos cada 6 meses'
  })
});

// Respuesta
{
  "fase": "DESPUÉS",
  "version": "MANTENIMIENTO_v2.5",
  "guardado_en_rag": true,
  "mensaje": "Ciclo PR cerrado..."
}
```

#### Consultar Conocimiento

```javascript
// POST /api/pr/consultar
const response = await fetch(`${PR_API_URL}/api/pr/consultar`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    pregunta: '¿Qué problemas ha tenido la CNC-05?',
    area: 'Mantenimiento',
    n_resultados: 5
  })
});

// Respuesta
{
  "respuesta": "Encontré 4 casos de CNC-05...",
  "casos_similares": [...],
  "total_en_rag": 150,
  "tiene_contexto": true
}
```

### Webhook para Notificaciones (Opcional)

Si PR-System necesita notificar al bot:

```javascript
// POST /webhook/notification (en el bot)
app.post('/webhook/notification', (req, res) => {
  const { tipo, destino, mensaje, datos } = req.body;

  switch(tipo) {
    case 'caso_urgente':
      notificarGrupo(destino, mensaje);
      break;
    case 'caso_atrasado':
      notificarSupervisor(destino, mensaje);
      break;
    case 'resumen_diario':
      enviarResumen(destino, datos);
      break;
  }

  res.json({ ok: true });
});
```

---

## 🔒 Seguridad

### Autenticación de Usuarios

```javascript
// Solo usuarios registrados pueden usar el bot
const user = getUserByPhone(phoneNumber);
if (!user) {
  await sendMessage(from,
    'No estás registrado en el sistema. ' +
    'Contacta al administrador.'
  );
  return;
}
```

### Validación de Grupos

```javascript
// Solo grupos autorizados
if (isGroup && !config.authorizedGroups.includes(groupId)) {
  return; // Ignorar mensaje
}
```

### Rate Limiting

```javascript
// Máximo 10 mensajes por minuto por usuario
const rateLimiter = new RateLimiter({
  windowMs: 60000,
  max: 10
});

if (!rateLimiter.allow(phoneNumber)) {
  await sendMessage(from,
    'Demasiados mensajes. Espera un momento.'
  );
  return;
}
```

### Sanitización de Inputs

```javascript
// Limpiar inputs antes de enviar a PR-System
const sanitize = (text) => {
  return text
    .replace(/<[^>]*>/g, '')  // Remover HTML
    .replace(/[^\w\sáéíóúñ.,!?-]/gi, '')  // Solo caracteres seguros
    .trim()
    .substring(0, 1000);  // Máximo 1000 caracteres
};
```

### Logs de Auditoría

```javascript
// Registrar todas las acciones
logger.info('Acción', {
  usuario: phoneNumber,
  comando: command,
  timestamp: new Date().toISOString(),
  resultado: 'éxito'
});
```

---

## 📊 Casos de Uso

### Caso 1: Planta de Manufactura

```
ESCENARIO:
- 50 operadores en 3 turnos
- 1 supervisor por turno
- Problemas frecuentes en máquinas CNC y soldadura

CONFIGURACIÓN:
- 1 número WhatsApp para el bot
- Grupo "Mantenimiento Urgente" para casos críticos
- Operadores reportan desde su celular personal

RESULTADOS (después de 3 meses):
- Casos documentados: +400%
- Tiempo de resolución: -35%
- Problemas recurrentes: -60%
```

### Caso 2: Empresa de Servicios

```
ESCENARIO:
- 20 técnicos en campo
- Resuelven problemas en sitio del cliente
- Necesitan acceso a historial de equipos

CONFIGURACIÓN:
- Técnicos consultan "/buscar equipo XYZ"
- Documentan solución al terminar
- Supervisores ven dashboard en tiempo real

RESULTADOS:
- Primera visita exitosa: +25%
- Llamadas de soporte: -40%
- Satisfacción cliente: +15%
```

---

## ❓ Solución de Problemas

### "El bot no responde"

```bash
# Verificar que el bot está corriendo
pm2 status

# Ver logs
pm2 logs whatsapp-bot

# Reiniciar
pm2 restart whatsapp-bot
```

### "Código QR no aparece"

```bash
# Eliminar sesión anterior
rm -rf data/sessions/*

# Reiniciar bot
npm start
```

### "Error de conexión con PR-System"

```bash
# Verificar que PR-System está corriendo
curl http://localhost:8000/health

# Verificar credenciales en .env
cat .env | grep PR_API
```

### "WhatsApp desvinculado"

1. Ir a WhatsApp en el teléfono
2. Configuración → Dispositivos vinculados
3. Eliminar sesión "PR-System Bot"
4. Reiniciar bot y escanear nuevo QR

---

## 🗺️ Roadmap

### Versión 1.0 (Actual)

- [x] Reportar problemas
- [x] Buscar casos similares
- [x] Cerrar ciclo PR
- [x] Comandos básicos
- [x] Autenticación de usuarios

### Versión 1.1 (Próxima)

- [ ] Envío de fotos como evidencia
- [ ] Notas de voz (transcripción)
- [ ] Notificaciones a grupos
- [ ] Dashboard de supervisor

### Versión 2.0 (Futuro)

- [ ] Múltiples idiomas
- [ ] Integración con sistemas externos (SAP, etc.)
- [ ] Análisis predictivo
- [ ] Reportes automáticos

---

## 📚 Referencias

- [Baileys Documentation](https://github.com/WhiskeySockets/Baileys)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [PR-System Documentation](../README.md)

---

## 📞 Soporte

- **Issues:** [github.com/srexcel/PR/issues](https://github.com/srexcel/PR/issues)
- **Documentación:** [docs/](.)

---

*Última actualización: Febrero 2024*
