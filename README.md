# AI Crypto Trading Assistant

Aplicacion web para trading de criptomonedas asistido por IA, iniciada en Fase 1 con paper trading. No promete ganancias, no ejecuta dinero real y prioriza trazabilidad, limites de riesgo y seguridad de secretos.

## Estado actual

- Backend FastAPI con login simple de administrador.
- SQLite local para desarrollo sin Docker.
- PostgreSQL preparado para despliegue futuro.
- Dashboard React/Vite/Tailwind.
- Modo DEMO funcional con operaciones paper.
- Modo REAL bloqueado intencionadamente en Fase 1.
- Datos de mercado mediante CCXT/Binance sandbox-testnet.
- Telegram por `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
- Historial de operaciones, decisiones, logs y configuracion de riesgo.
- Motor de riesgo obligatorio antes de abrir una operacion paper.

## Requisitos

- Python 3.12+.
- Node.js 22+ o Node.js LTS reciente.
- No necesitas Docker para la Fase 1.

## Ejecutar sin Docker en Linux Mint

1. Instala dependencias del sistema:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip nodejs npm
```

Si tu repositorio instala una version antigua de Node, instala Node.js LTS desde NodeSource y despues comprueba:

```bash
node --version
npm --version
python3 --version
```

2. Entra en la carpeta del proyecto y da permisos a los scripts:

```bash
chmod +x scripts/*.sh
```

3. Prepara e inicia la app:

```bash
./scripts/setup-local.sh
./scripts/start-local.sh
```

Servicios:

- Frontend: http://127.0.0.1:5173
- Backend: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

## Servidor para toda tu WiFi en Linux Mint

Para dejarlo corriendo en un servidor y abrirlo desde cualquier PC/movil de tu red WiFi:

```bash
chmod +x scripts/*.sh scripts/linux/*.sh
./scripts/linux/install-systemd-lan.sh
```

El instalador hace esto:

- Usa SQLite local en `backend/dev_trading.db`.
- Configura el frontend para llamar automaticamente a la IP del servidor.
- Arranca el backend en `0.0.0.0:8000`.
- Arranca el frontend en `0.0.0.0:5173`.
- Crea servicios `systemd`:
  - `ai-crypto-backend.service`
  - `ai-crypto-frontend.service`
- Activa reinicio automatico con `Restart=always`.
- Espera a `network-online.target`, util si el servidor reinicia o pierde WiFi.
- Si `ufw` existe, abre los puertos solo para rangos privados LAN.

Para ver la URL del servidor:

```bash
hostname -I
```

Abre desde tu PC:

```text
http://IP_DEL_SERVIDOR:5173
```

Comandos utiles:

```bash
./scripts/linux/status-systemd-lan.sh
./scripts/linux/check-lan-ports.sh
./scripts/linux/open-lan-ports.sh
./scripts/linux/restart-systemd-lan.sh
sudo systemctl restart ai-crypto-backend ai-crypto-frontend
journalctl -u ai-crypto-backend -f
journalctl -u ai-crypto-frontend -f
```

Si los servicios no arrancan porque los puertos `8000` o `5173` estan ocupados:

```bash
./scripts/linux/free-lan-ports.sh
./scripts/linux/free-lan-ports.sh --kill
./scripts/linux/restart-systemd-lan.sh
```

El primer comando solo muestra que procesos ocupan los puertos. El segundo los para de forma explicita.

Para quitar los servicios:

```bash
./scripts/linux/uninstall-systemd-lan.sh
```

Si el login muestra `Failed to fetch`, normalmente el frontend esta intentando llamar al backend equivocado. En el servidor ejecuta:

```bash
grep VITE_API_BASE_URL frontend/.env
curl http://127.0.0.1:8000/health
```

Para uso en WiFi, `frontend/.env` debe quedar asi:

```env
VITE_API_BASE_URL=
```

Despues reinicia:

```bash
sudo systemctl restart ai-crypto-backend ai-crypto-frontend
```

Seguridad recomendada para uso en WiFi:

- Usa una contrasena de admin fuerte en `backend/.env`.
- No abras los puertos 5173/8000 en el router hacia internet.
- Manten el modo `REAL` desactivado; en Fase 1 sigue bloqueado por API.
- Si cambias de red WiFi, revisa la IP con `hostname -I`.

## Ejecutar sin Docker en Windows

La forma mas sencilla:

```powershell
.\scripts\setup-local.ps1
.\scripts\start-local.ps1
```

Tambien puedes hacer doble clic en:

- `scripts\setup-local.bat`
- `scripts\start-local.bat`

Esto crea el entorno virtual de Python, instala dependencias del backend, instala dependencias del frontend, usa SQLite local en `backend/dev_trading.db` y abre el dashboard.

Servicios:

- Frontend: http://127.0.0.1:5173
- Backend: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

## Configuracion manual

1. Copia variables de entorno:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

2. Edita `backend/.env`:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=usa-una-password-larga
AUTH_SECRET_KEY=usa-un-secreto-largo-aleatorio
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
BINANCE_TESTNET_API_KEY=
BINANCE_TESTNET_SECRET=
```

Las claves reales de Binance existen en el `.env.example` para fases futuras, pero no se usan en Fase 1. Si en el futuro se activan, deben tener permisos minimos: lectura y spot trading, sin withdrawal/retiro.

## Ejecutar localmente

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Ejecutar con Docker, opcional

Docker no es necesario. Si alguna vez lo tienes disponible:

```bash
docker compose up --build
```

## Uso basico

1. Entra en http://localhost:5173.
2. Inicia sesion con `ADMIN_USERNAME` y `ADMIN_PASSWORD`.
3. Comprueba que el modo sea `DEMO`.
4. Pulsa `ON`.
5. Pulsa `Tick demo` para ejecutar un ciclo.
6. Si el modo es `MANUAL`, confirma la compra desde la tabla de operaciones.
7. Revisa historial, decisiones y logs.

## Endpoints principales

- `POST /auth/login`
- `GET /bot/status`
- `POST /bot/start`
- `POST /bot/stop`
- `POST /bot/mode/demo`
- `POST /bot/mode/real` bloqueado en Fase 1
- `POST /bot/mode/manual`
- `POST /bot/mode/autonomous`
- `POST /bot/tick`
- `GET /settings/risk`
- `PUT /settings/risk`
- `GET /trades/open`
- `GET /trades/history`
- `POST /trades/{id}/confirm-buy`
- `POST /trades/{id}/confirm-sell`
- `POST /trades/{id}/convert-long-term`
- `GET /ai/decisions`
- `GET /logs`
- `POST /telegram/test`

## Scheduler

Por defecto el ciclo automatico no arranca solo. Para activarlo:

```env
AUTO_START_SCHEDULER=true
BOT_INTERVAL_SECONDS=60
```

Incluso con scheduler activo, el bot solo opera si esta `ON` y en `DEMO`.

## Seguridad

- No guardes API keys en frontend.
- No subas `.env` a git.
- No des permisos de retiro a ninguna API key.
- El modo real requiere una fase posterior con confirmacion fuerte, auditoria adicional y pruebas.
- Todos los eventos relevantes se registran en SQLite local en Fase 1, o PostgreSQL si cambias `DATABASE_URL`.

## Arquitectura

Consulta [ARCHITECTURE.md](./ARCHITECTURE.md) para el modelo de datos, flujo de bot y decisiones de seguridad aplicadas.
