# Arquitectura

Esta Fase 1 implementa solo paper trading y funciona sin Docker usando SQLite local. El modo real existe como endpoint protegido, pero responde `403` aunque se envie la confirmacion fuerte. La activacion real queda deliberadamente para la Fase 4.

## Ajustes de seguridad aplicados a la especificacion

- El valor por defecto es `DEMO` y `MANUAL`; `REAL` no se puede activar en Fase 1.
- El frontend nunca recibe ni guarda API keys.
- Los logs pasan por una funcion de redaccion para campos con `secret`, `token`, `key`, `password` o `signature`.
- Telegram guarda resultado de envio, pero no expone tokens.
- El bot no ejecuta ordenes reales; registra ordenes `paper` en `exchange_order`.
- La base de datos local por defecto es `backend/dev_trading.db`; PostgreSQL queda preparado para despliegue futuro.
- El motor de riesgo es obligatorio incluso cuando la propuesta nace de reglas internas.
- La IA de Fase 2 debera devolver JSON; si faltan datos, `WAIT`.
- La arquitectura separa `exchange`, `ai`, `risk`, `telegram` y `trading` para poder anadir Kraken y proveedores IA sin reescribir el nucleo.

## Componentes

- `backend/app/main.py`: aplicacion FastAPI, CORS, startup y routers.
- `backend/app/models/db.py`: modelos SQLModel para estado, riesgo, trades, ordenes, balances, decisiones, logs, Telegram y cambios de modo.
- `backend/app/services/exchange/binance.py`: datos de mercado mediante CCXT en sandbox/testnet.
- `backend/app/services/risk/engine.py`: validacion obligatoria de propuestas.
- `backend/app/services/trading/demo.py`: ciclo paper trading y mark-to-market.
- `backend/app/services/telegram/service.py`: notificaciones Telegram por variables de entorno.
- `frontend/src/pages/Dashboard.jsx`: dashboard operativo con estado, switches, riesgo, operaciones, historial, decisiones y logs.
- `scripts/*.ps1` y `scripts/*.bat`: instalacion y arranque local en Windows sin Docker.
- `scripts/*.sh`: instalacion y arranque local en Linux Mint sin Docker.
- `scripts/linux/install-systemd-lan.sh`: instala servicios `systemd` para exponer la app en la red WiFi y reiniciarla automaticamente.
- `scripts/linux/restart-systemd-lan.sh`, `check-lan-ports.sh`, `open-lan-ports.sh` y `free-lan-ports.sh`: mantenimiento operativo de servicios, puertos y firewall LAN.
- `scripts/linux/update-app.sh`: actualizacion por `git pull --ff-only` sin borrar `.env`, SQLite ni reclonar.

## Modelo de datos principal

- `botstate`: `enabled`, `trading_mode`, `control_mode`, confirmacion de real y fecha de actualizacion.
- `risksettings`: limites diarios, perdida maxima, objetivo, maximo de abiertas, maximo por operacion, spread, volumen y listas permitidas/bloqueadas.
- `risksettingshistory`: snapshot historico de cada cambio de riesgo.
- `trade`: posicion paper o futura real con entrada, precio actual, PnL, estado, razones y timestamps.
- `exchangeorder`: orden enviada o simulada, payload de request/response y modo.
- `aidecision`: recomendacion estructurada, proveedor, accion, confianza, razon y JSON bruto.
- `balancesnapshot`: snapshot de balance para futuras fases.
- `modechange`: auditoria de cambios DEMO/REAL y MANUAL/AUTONOMOUS.
- `telegrammessage`: mensajes enviados y resultado.
- `logentry`: eventos internos redactados.

## Flujo Fase 1

1. El usuario inicia sesion en el dashboard.
2. Enciende el bot en `DEMO`.
3. Ejecuta un tick manual o activa scheduler con `AUTO_START_SCHEDULER=true`.
4. El backend obtiene tickers de Binance sandbox/testnet por CCXT.
5. El selector interno filtra por volumen, spread y cambio positivo.
6. Se crea una decision `rules_v1` con estructura compatible con la futura IA.
7. El motor de riesgo acepta o rechaza.
8. En `MANUAL`, queda como `PROPOSED` y requiere confirmacion.
9. En `AUTONOMOUS`, se abre como operacion paper si pasa riesgo.
10. Todo queda registrado y se notifica por Telegram si esta configurado.

## Fases siguientes

- Fase 2: integrar OpenRouter/NVIDIA, parseo estricto JSON y confirmacion manual por dashboard/Telegram.
- Fase 2 parcial implementada: OpenRouter con Gemini 2.5 Flash-Lite, fallback DeepSeek V3.1, JSON estricto, costes diarios, datos de mercado controlados y switch IA demo.
- Fase 3: autonomo demo completo, backtesting simple y reglas de salida mas ricas.
- Fase 4: Binance real protegido, confirmacion fuerte persistente, limites diarios estrictos y permisos minimos.
- Fase 5: Kraken, largo plazo separado, estadisticas avanzadas.
