# PR_BAILEYS: Integración WhatsApp

**Versión:** 1.0
**Prioridad:** P2 - ALTA
**Dependencias:** PR_CODIGO (P1), Node.js 18+

---

## 1. OBJETIVO

Permitir que los usuarios interactúen con PR-System **desde WhatsApp**, donde realmente trabajan.

> "El mejor sistema es el que no requiere que cambies tu forma de trabajar"

---

## 2. ¿POR QUÉ BAILEYS?

| Opción | Costo | Limitaciones | Veredicto |
|--------|-------|--------------|-----------|
| WhatsApp Business API | $$$$ | Requiere aprobación Meta | NO |
| Twilio WhatsApp | $$$ | Templates pre-aprobados | NO |
| **Baileys** | GRATIS | Cuenta personal como bot | SÍ |

**Baileys** es una librería Node.js que conecta WhatsApp Web via WebSocket.
- Open source
- Sin costos
- Sin aprobaciones
- Funciona con cuenta normal

---

## 3. ARQUITECTURA

```
┌─────────────────────────────────────────────────────────────┐
│                     WhatsApp Users                          │
│   📱 Operario    📱 Supervisor    📱 Admin                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ WhatsApp Web Protocol
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  BAILEYS SERVICE                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │   Socket    │ │   Session   │ │   Message Handler   │   │
│  │   Manager   │ │   Store     │ │   (PR Commands)     │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PR-SYSTEM BACKEND                          │
│                    (FastAPI)                                │
│   /api/pr/problema  →  PRAgent  →  ChromaDB + SQLite       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. ESTRUCTURA DEL PROYECTO

```
PR/
├── main.py                    # Backend Python (existente)
├── pr_agent/                  # Lógica PR (de PR_CODIGO)
│
└── channels/
    └── whatsapp/
        ├── package.json       # Dependencias Node.js
        ├── src/
        │   ├── index.js       # Punto de entrada
        │   ├── bot.js         # Lógica del bot
        │   ├── commands.js    # Comandos PR
        │   ├── session.js     # Gestión de sesión
        │   └── api.js         # Cliente API PR-System
        ├── auth/              # Datos de sesión (gitignore)
        │   └── session.json
        └── .env               # Configuración
```

---

## 5. IMPLEMENTACIÓN

### 5.1 package.json

```json
{
  "name": "pr-whatsapp",
  "version": "1.0.0",
  "description": "Canal WhatsApp para PR-System",
  "main": "src/index.js",
  "type": "module",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js"
  },
  "dependencies": {
    "@whiskeysockets/baileys": "^6.7.0",
    "qrcode-terminal": "^0.12.0",
    "pino": "^8.16.0",
    "axios": "^1.6.0",
    "dotenv": "^16.3.1"
  }
}
```

### 5.2 Configuración (.env)

```env
# PR-System Backend
PR_API_URL=http://localhost:8000
PR_API_USER=whatsapp_bot
PR_API_PASS=secure_password_here

# WhatsApp
WA_SESSION_NAME=pr-system-bot
WA_ALLOWED_NUMBERS=+521234567890,+521234567891

# Logging
LOG_LEVEL=info
```

### 5.3 index.js (Punto de entrada)

```javascript
// channels/whatsapp/src/index.js

import 'dotenv/config';
import { createBot } from './bot.js';
import { logger } from './logger.js';

async function main() {
    logger.info('='.repeat(50));
    logger.info('PR-System WhatsApp Bot');
    logger.info('='.repeat(50));

    try {
        const bot = await createBot();

        // Graceful shutdown
        process.on('SIGINT', async () => {
            logger.info('Cerrando bot...');
            await bot.close();
            process.exit(0);
        });

    } catch (error) {
        logger.error('Error iniciando bot:', error);
        process.exit(1);
    }
}

main();
```

### 5.4 bot.js (Lógica principal)

```javascript
// channels/whatsapp/src/bot.js

import makeWASocket, {
    DisconnectReason,
    useMultiFileAuthState,
    makeInMemoryStore
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import qrcode from 'qrcode-terminal';
import { handleMessage } from './commands.js';
import { logger } from './logger.js';

const store = makeInMemoryStore({});

export async function createBot() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth');

    const socket = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        logger: logger.child({ module: 'baileys' }),
    });

    store.bind(socket.ev);

    // Evento: Actualización de conexión
    socket.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            logger.info('Escanea el código QR con WhatsApp:');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;

            if (reason === DisconnectReason.loggedOut) {
                logger.error('Sesión cerrada. Elimina ./auth y reinicia.');
            } else {
                logger.info('Reconectando...');
                await createBot();
            }
        }

        if (connection === 'open') {
            logger.info('✓ Conectado a WhatsApp');
            logger.info('Bot PR-System listo para recibir mensajes');
        }
    });

    // Evento: Credenciales actualizadas
    socket.ev.on('creds.update', saveCreds);

    // Evento: Mensaje recibido
    socket.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            // Ignorar mensajes propios
            if (msg.key.fromMe) continue;

            // Ignorar mensajes de grupos (opcional)
            if (msg.key.remoteJid.endsWith('@g.us')) continue;

            // Procesar mensaje
            await handleMessage(socket, msg);
        }
    });

    return {
        socket,
        close: async () => {
            socket.end();
        }
    };
}
```

### 5.5 commands.js (Comandos PR)

```javascript
// channels/whatsapp/src/commands.js

import { PRApiClient } from './api.js';
import { logger } from './logger.js';

const api = new PRApiClient();

// Estado de conversación por usuario
const userSessions = new Map();

/**
 * Manejador principal de mensajes
 */
export async function handleMessage(socket, msg) {
    const remoteJid = msg.key.remoteJid;
    const text = msg.message?.conversation ||
                 msg.message?.extendedTextMessage?.text ||
                 '';

    if (!text.trim()) return;

    const numero = remoteJid.replace('@s.whatsapp.net', '');
    logger.info(`[${numero}]: ${text}`);

    try {
        // Obtener o crear sesión de usuario
        let session = userSessions.get(numero) || {
            estado: 'idle',
            datos: {}
        };

        // Procesar según estado
        const respuesta = await procesarMensaje(text, session, numero);

        // Actualizar sesión
        userSessions.set(numero, session);

        // Enviar respuesta
        await socket.sendMessage(remoteJid, { text: respuesta });

    } catch (error) {
        logger.error(`Error procesando mensaje: ${error}`);
        await socket.sendMessage(remoteJid, {
            text: '❌ Ocurrió un error. Intenta de nuevo.'
        });
    }
}

/**
 * Procesa mensaje según estado de conversación
 */
async function procesarMensaje(texto, session, numero) {
    const textoLower = texto.toLowerCase().trim();

    // Comandos globales (funcionan en cualquier estado)
    if (textoLower === 'ayuda' || textoLower === 'help' || textoLower === '?') {
        return mostrarAyuda();
    }

    if (textoLower === 'cancelar' || textoLower === 'salir') {
        session.estado = 'idle';
        session.datos = {};
        return '✅ Operación cancelada. ¿En qué puedo ayudarte?';
    }

    // Procesar según estado actual
    switch (session.estado) {
        case 'idle':
            return await procesarComandoInicial(texto, session);

        case 'esperando_descripcion':
            return await procesarDescripcion(texto, session, numero);

        case 'esperando_area':
            return await procesarArea(texto, session, numero);

        case 'confirmando_caso':
            return await procesarConfirmacion(texto, session, numero);

        case 'documentando':
            return await procesarDocumentacion(texto, session, numero);

        default:
            session.estado = 'idle';
            return mostrarAyuda();
    }
}

/**
 * Procesa comando inicial
 */
async function procesarComandoInicial(texto, session) {
    const textoLower = texto.toLowerCase();

    // Detectar intención de reportar problema
    const palabrasProblema = [
        'problema', 'falla', 'error', 'defecto', 'ayuda',
        'no funciona', 'se detuvo', 'no arranca', 'está mal'
    ];

    if (palabrasProblema.some(p => textoLower.includes(p))) {
        session.estado = 'esperando_descripcion';
        return `📋 *Nuevo Reporte PR*

Describe el problema con el mayor detalle posible:
- ¿Qué está pasando?
- ¿Cuándo empezó?
- ¿Qué equipo/área?

_Escribe "cancelar" para salir_`;
    }

    // Consultar base de conocimiento
    if (textoLower.includes('buscar') || textoLower.includes('consultar')) {
        const query = texto.replace(/buscar|consultar/gi, '').trim();
        if (query) {
            return await buscarEnRAG(query);
        }
        return '🔍 ¿Qué quieres buscar en la base de conocimiento?';
    }

    // Ver estadísticas
    if (textoLower.includes('estadisticas') || textoLower.includes('stats')) {
        return await obtenerEstadisticas();
    }

    // No entendido - mostrar ayuda
    return mostrarAyuda();
}

/**
 * Procesa descripción del problema
 */
async function procesarDescripcion(texto, session, numero) {
    if (texto.length < 10) {
        return '⚠️ La descripción es muy corta. Por favor, da más detalles.';
    }

    session.datos.descripcion = texto;
    session.estado = 'esperando_area';

    return `📍 *¿En qué área ocurre?*

Opciones comunes:
1. Producción
2. Calidad
3. Mantenimiento
4. Logística
5. Otra (escríbela)

_Responde con el número o nombre del área_`;
}

/**
 * Procesa área del problema
 */
async function procesarArea(texto, session, numero) {
    const areas = {
        '1': 'Producción',
        '2': 'Calidad',
        '3': 'Mantenimiento',
        '4': 'Logística',
        'produccion': 'Producción',
        'calidad': 'Calidad',
        'mantenimiento': 'Mantenimiento',
        'logistica': 'Logística'
    };

    const area = areas[texto.toLowerCase()] || texto;
    session.datos.area = area;

    // Buscar casos similares
    const resultado = await api.reportarProblema(
        session.datos.descripcion,
        area,
        numero
    );

    if (resultado.casos_similares && resultado.casos_similares.length > 0) {
        session.estado = 'confirmando_caso';
        session.datos.resultado = resultado;

        let respuesta = `🔍 *Encontré ${resultado.casos_similares.length} caso(s) similar(es):*\n\n`;

        resultado.casos_similares.forEach((caso, i) => {
            respuesta += `*${i + 1}. ${caso.version || 'Caso'}*\n`;
            respuesta += `   📅 ${caso.fecha || 'N/A'}\n`;
            respuesta += `   📝 ${caso.resumen?.substring(0, 100)}...\n\n`;
        });

        respuesta += `¿Alguno de estos casos aplica a tu situación?\n`;
        respuesta += `Responde: *sí* (ver detalles) o *no* (crear nuevo)`;

        return respuesta;
    } else {
        session.estado = 'documentando';
        session.datos.incidencia_id = resultado.incidencia_id;

        return `📝 *Caso Nuevo Registrado*

No encontré casos similares. Vamos a documentar este problema.

${resultado.preguntas_guia ? resultado.preguntas_guia.map((p, i) => `${i + 1}. ${p}`).join('\n') : ''}

Por favor, proporciona más detalles.`;
    }
}

/**
 * Procesa confirmación de caso similar
 */
async function procesarConfirmacion(texto, session, numero) {
    const textoLower = texto.toLowerCase();

    if (textoLower === 'si' || textoLower === 'sí' || textoLower === 'yes') {
        const caso = session.datos.resultado.casos_similares[0];

        session.estado = 'idle';
        session.datos = {};

        return `✅ *Caso Similar Encontrado*

*${caso.version}*

${caso.contenido || caso.resumen}

---
_Si esto resolvió tu problema, no necesitas hacer nada más._
_Si es diferente, escribe "problema" para crear uno nuevo._`;
    }

    if (textoLower === 'no') {
        session.estado = 'documentando';

        return `📝 *Creando Caso Nuevo*

Entendido, este es un caso diferente.

Por favor, describe qué hace diferente a tu situación:`;
    }

    return 'Por favor responde *sí* o *no*';
}

/**
 * Procesa documentación adicional
 */
async function procesarDocumentacion(texto, session, numero) {
    // Agregar reporte a la incidencia
    await api.agregarReporte(
        session.datos.incidencia_id,
        texto,
        numero
    );

    session.estado = 'idle';
    const incidenciaId = session.datos.incidencia_id;
    session.datos = {};

    return `✅ *Información Agregada*

Tu reporte ha sido registrado.

📌 ID: ${incidenciaId?.substring(0, 8)}...

Un supervisor revisará el caso y documentará la solución.
Cuando se resuelva, quedará guardado en la base de conocimiento.

_Escribe "problema" si tienes otro tema._`;
}

/**
 * Busca en la base de conocimiento
 */
async function buscarEnRAG(query) {
    try {
        const resultado = await api.consultarRAG(query);

        if (!resultado.casos_similares || resultado.casos_similares.length === 0) {
            return `🔍 No encontré casos relacionados con "${query}".\n\n¿Quieres reportar un problema? Escribe "problema".`;
        }

        let respuesta = `🔍 *Resultados para "${query}":*\n\n`;

        resultado.casos_similares.slice(0, 3).forEach((caso, i) => {
            respuesta += `*${i + 1}. ${caso.metadata?.titulo || 'Caso'}*\n`;
            respuesta += `${caso.contenido?.substring(0, 200)}...\n\n`;
        });

        if (resultado.respuesta) {
            respuesta += `---\n💡 *Resumen:*\n${resultado.respuesta}`;
        }

        return respuesta;

    } catch (error) {
        return '❌ Error consultando la base de conocimiento.';
    }
}

/**
 * Obtiene estadísticas del sistema
 */
async function obtenerEstadisticas() {
    try {
        const stats = await api.obtenerStats();

        return `📊 *Estadísticas PR-System*

📚 Documentos en RAG: ${stats.total_documentos || 0}
🔧 Casos resueltos: ${stats.casos_resueltos || 0}
📝 Incidencias activas: ${stats.incidencias_activas || 0}

_El sistema aprende de cada caso resuelto._`;

    } catch (error) {
        return '❌ Error obteniendo estadísticas.';
    }
}

/**
 * Muestra ayuda
 */
function mostrarAyuda() {
    return `🤖 *PR-System Bot*

Comandos disponibles:

📋 *problema* - Reportar un nuevo problema
🔍 *buscar [texto]* - Buscar en base de conocimiento
📊 *estadisticas* - Ver estadísticas del sistema
❌ *cancelar* - Cancelar operación actual
❓ *ayuda* - Mostrar este mensaje

---
_Sistema de Conocimiento Vivo_
_"¿Qué aprendimos la última vez?"_`;
}
```

### 5.6 api.js (Cliente API)

```javascript
// channels/whatsapp/src/api.js

import axios from 'axios';
import { logger } from './logger.js';

export class PRApiClient {
    constructor() {
        this.baseURL = process.env.PR_API_URL || 'http://localhost:8000';
        this.token = null;

        this.client = axios.create({
            baseURL: this.baseURL,
            timeout: 30000,
        });
    }

    async authenticate() {
        if (this.token) return;

        try {
            const response = await this.client.post('/api/auth/login',
                new URLSearchParams({
                    username: process.env.PR_API_USER,
                    password: process.env.PR_API_PASS
                }),
                {
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                }
            );

            this.token = response.data.access_token;
            this.client.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
            logger.info('Autenticado con PR-System API');

        } catch (error) {
            logger.error('Error autenticando:', error.message);
            throw error;
        }
    }

    async reportarProblema(descripcion, area, usuario) {
        await this.authenticate();

        try {
            const response = await this.client.post('/api/pr/problema',
                new URLSearchParams({
                    descripcion,
                    area,
                }),
            );
            return response.data;
        } catch (error) {
            logger.error('Error reportando problema:', error.message);
            throw error;
        }
    }

    async agregarReporte(incidenciaId, contenido, autor) {
        await this.authenticate();

        try {
            const response = await this.client.post(
                `/api/incidencias/${incidenciaId}/reportes`,
                { autor, contenido }
            );
            return response.data;
        } catch (error) {
            logger.error('Error agregando reporte:', error.message);
            throw error;
        }
    }

    async consultarRAG(pregunta) {
        await this.authenticate();

        try {
            const response = await this.client.post('/api/rag/consultar', {
                pregunta,
                n_resultados: 5
            });
            return response.data;
        } catch (error) {
            logger.error('Error consultando RAG:', error.message);
            throw error;
        }
    }

    async obtenerStats() {
        await this.authenticate();

        try {
            const response = await this.client.get('/api/rag/stats');
            return response.data;
        } catch (error) {
            logger.error('Error obteniendo stats:', error.message);
            throw error;
        }
    }
}
```

### 5.7 logger.js

```javascript
// channels/whatsapp/src/logger.js

import pino from 'pino';

export const logger = pino({
    level: process.env.LOG_LEVEL || 'info',
    transport: {
        target: 'pino-pretty',
        options: {
            colorize: true,
            translateTime: 'SYS:standard',
        }
    }
});
```

---

## 6. FLUJO DE CONVERSACIÓN

```
USUARIO                           BOT
────────────────────────────────────────────────────────

"Hola"
                                  🤖 PR-System Bot

                                  Comandos disponibles:
                                  📋 problema - Reportar
                                  🔍 buscar [texto] - Buscar
                                  ...

"Tenemos un problema con
la soldadura"
                                  📋 Nuevo Reporte PR

                                  Describe el problema con
                                  el mayor detalle posible...

"La soldadura en línea 3
está generando defectos
de porosidad desde las 8am"
                                  📍 ¿En qué área ocurre?

                                  1. Producción
                                  2. Calidad
                                  ...

"1"
                                  🔍 Encontré 2 caso(s) similar(es):

                                  1. SOLDADURA_v1.2
                                     📅 Dic 2024
                                     📝 Defectos de porosidad...

                                  ¿Alguno aplica? sí/no

"sí"
                                  ✅ Caso Similar Encontrado

                                  SOLDADURA_v1.2

                                  Problema: Porosidad en soldadura
                                  Causa: Gas de protección
                                  Solución: Verificar flujo...
```

---

## 7. INSTALACIÓN

```bash
# 1. Ir al directorio
cd PR/channels/whatsapp

# 2. Instalar dependencias
npm install

# 3. Configurar .env
cp .env.example .env
nano .env

# 4. Crear usuario bot en PR-System
# (desde el admin web o directamente en BD)

# 5. Iniciar
npm start

# 6. Escanear QR con WhatsApp
# (aparece en terminal)
```

---

## 8. CONSIDERACIONES DE SEGURIDAD

| Riesgo | Mitigación |
|--------|------------|
| Acceso no autorizado | Lista blanca de números en .env |
| Sesión robada | Archivo auth/ fuera de repo (gitignore) |
| Spam | Rate limiting por número |
| Datos sensibles | Todo local, nada a servidores externos |

---

## 9. CHECKLIST

- [ ] Crear estructura `channels/whatsapp/`
- [ ] Implementar `package.json`
- [ ] Implementar `bot.js`
- [ ] Implementar `commands.js`
- [ ] Implementar `api.js`
- [ ] Crear usuario bot en PR-System
- [ ] Configurar `.env`
- [ ] Probar conexión WhatsApp
- [ ] Probar flujo completo

---

*Este documento es checkpoint v1.0 de PR_BAILEYS*
*v1.1 viene después del siguiente error*
