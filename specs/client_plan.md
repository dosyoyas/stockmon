# Plan: StockMon Client (Raspberry Pi)

## Contexto

Cliente que corre en Raspberry Pi, consulta la API de StockMon periódicamente y envía notificaciones por email cuando hay alertas. Mantiene localmente la configuración de tickers y el registro de alertas ya notificadas para evitar spam.

**Nota**: El cliente vive en el mismo repositorio que la API, en el directorio `client/`.

## Stack

- **Python 3.x**
- **Requests** - Llamadas HTTP a la API
- **smtplib** o servicio externo - Envío de emails
- **Cron** - Ejecución periódica
- **pytest** - Testing framework
- **responses** - Mock HTTP requests

## Estructura de archivos

```
stockmon/
└── client/
    ├── __init__.py
    ├── main.py            # Script principal
    ├── config.json        # Tickers y umbrales
    └── notified.json      # Alertas ya notificadas (auto-generado)

# Tests en tests/test_client.py (mismo directorio de tests que la API)
# Variables de entorno en .env (raíz del proyecto)
```

## Configuración

**config.json:**
```json
{
  "api_url": "https://stockmon.up.railway.app/check-alerts",
  "silence_hours": 48,
  "tickers": {
    "AAPL": {"buy": 170, "sell": 190},
    "MSFT": {"buy": 400, "sell": 420}
  }
}
```

**Nota**: `api_url` puede ser sobreescrito con la variable de entorno `API_URL` para testing local.

**.env:** (en la raíz del proyecto, compartido con API)
```
# API
API_KEY=tu-clave-secreta

# Cliente (solo necesario en Raspberry Pi)
SMTP_HOST=smtp.gmail.com
SMTP_USER=tu@email.com
SMTP_PASS=app-password
NOTIFY_EMAIL=destino@email.com
```

## Flujo de ejecución

1. Leer `config.json` con tickers y umbrales
2. Llamar a la API (timeout 90s por cold start)
3. Si `service_degraded: true` → notificar "YFinance roto, revisar API"
4. Si `market_open: false` → no hacer nada (opcional: log)
5. Filtrar alertas ya notificadas (consultar `notified.json`)
6. Si hay alertas nuevas:
   - Enviar email con las alertas
   - Actualizar `notified.json` con timestamp
7. Limpiar entradas antiguas de `notified.json` (> silence_hours)

## Registro de alertas notificadas

**notified.json:**
```json
{
  "AAPL": {
    "buy": "2024-02-06T10:00:00Z"
  },
  "MSFT": {
    "sell": "2024-02-05T14:30:00Z"
  }
}
```

Antes de notificar, verificar si `now - notified_at < silence_hours`.

## Cron

Ejecutar cada 15 minutos (ajustable):

```cron
*/15 * * * * cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main >> /home/pi/stockmon/logs/client.log 2>&1
```

**Nota**: El cron corre 24/7. La API devuelve `market_open: false` fuera de horario, el cliente simplemente no notifica nada.

## Formato del email

```
Asunto: StockMon Alert: AAPL buy signal

Cuerpo:
Ticker: AAPL
Tipo: BUY
Umbral: $170.00
Alcanzado: $168.50
Actual: $172.30

---
Generado por StockMon
```

## Email especial: Servicio degradado

Si `service_degraded: true`:

```
Asunto: StockMon: Servicio degradado - Revisar API

Cuerpo:
YFinance parece no funcionar. Todos los tickers fallaron.
Es probable que necesites actualizar las dependencias de la API.
```

## CLI Arguments

```bash
# Ejecución normal (producción)
python client.py

# Dry run: no envía emails, imprime a stdout
python client.py --dry-run

# Usar API local para desarrollo
API_URL=http://localhost:8000/check-alerts python client.py --dry-run
```

**Flags:**
- `--dry-run`: No envía emails, imprime alertas a stdout. No actualiza `notified.json`.

## Testing

### Estrategia de testing

El proyecto incluye dos tipos de tests para el cliente:

1. **Tests unitarios con mocks**: Tests rápidos que mockean las llamadas HTTP a la API y el envío de emails
2. **Tests de integración con Docker**: Tests que ejecutan el cliente contra una API real levantada en Docker, sin mocks de HTTP

### Tests unitarios (existentes)

Mockear llamadas HTTP a la API y el envío de emails. Nunca hacer llamadas reales en tests unitarios.

### Fixtures (conftest.py)

```python
@pytest.fixture
def mock_api_response():
    """Mock respuesta de la API con alertas"""

@pytest.fixture
def mock_api_degraded():
    """Mock respuesta con service_degraded: true"""

@pytest.fixture
def mock_smtp(monkeypatch):
    """Mock smtplib para capturar emails enviados"""

@pytest.fixture
def temp_notified_file(tmp_path):
    """Archivo notified.json temporal para tests"""
```

### Test cases

**test_client.py:**
- API retorna alertas nuevas → envía email
- API retorna `market_open: false` → no envía email
- API retorna `service_degraded: true` → envía email de advertencia
- API retorna error 401 → log de error, no crash
- API timeout → manejo graceful
- `--dry-run` → imprime a stdout, no envía email

**test_notified.py:**
- Alerta nueva (no en notified.json) → se notifica
- Alerta reciente (< silence_hours) → no se notifica
- Alerta antigua (> silence_hours) → se notifica de nuevo
- Limpieza de entradas antiguas funciona correctamente

### Ejecución de tests unitarios

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecutar tests unitarios del cliente
pytest tests/test_client.py tests/test_notified.py -v

# Con coverage
pytest tests/test_client.py tests/test_notified.py --cov=client --cov-report=term-missing
```

### Tests de integración con Docker

Los tests de integración del cliente ejecutan llamadas reales contra la API levantada en Docker, sin mockear las requests HTTP. Los emails sí se mockean para evitar envíos reales.

**Ver sección de "Tests de integración con Docker" en `api_plan.md`** para detalles de la configuración de Docker.

**Tests del cliente:**
Los tests de integración del cliente (`test_integration_docker.py`) verifican:
- Cliente se conecta exitosamente a la API en Docker
- Cliente maneja respuestas reales de la API (alertas, market_open, etc.)
- Cliente maneja errores de autenticación (401)
- Cliente maneja timeouts y errores de red
- Flujo completo cliente → API sin mocks de HTTP

**Ejecución:**

```bash
# Ejecutar tests de integración con Docker
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Los tests del cliente se ejecutan automáticamente después de que la API esté lista
```

### Testing manual contra API local

```bash
# Terminal 1: Levantar API localmente (desde raíz del proyecto)
uvicorn app.main:app --reload

# Terminal 2: Ejecutar cliente en dry-run
API_URL=http://localhost:8000/check-alerts python -m client.main --dry-run
```

## Development Setup

El cliente usa el mismo entorno virtual que la API.

```bash
# Desde la raíz del proyecto (ya con venv activado)
source venv/bin/activate

# Ejecutar cliente
python -m client.main --dry-run

# Ejecutar contra API local
API_URL=http://localhost:8000/check-alerts python -m client.main --dry-run
```

### Setup en Raspberry Pi

```bash
# Clonar repositorio
git clone https://github.com/dosyoyas/stockmon.git
cd stockmon

# Crear entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar solo dependencias de producción
pip install -r requirements.txt

# Configurar .env con credenciales
cp .env.example .env
nano .env  # Agregar API_KEY, SMTP_*, NOTIFY_EMAIL

# Crear directorio de logs
mkdir -p logs

# Configurar cron
crontab -e
# Agregar: */15 * * * * cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main >> /home/pi/stockmon/logs/client.log 2>&1
```

## Variables de entorno (Cliente)

| Variable | Descripción | Requerida | Default |
|----------|-------------|-----------|---------|
| `API_KEY` | Clave para autenticar con la API | Sí | - |
| `API_URL` | Override de api_url en config.json | No | config.json |
| `SMTP_HOST` | Servidor SMTP | Sí | - |
| `SMTP_USER` | Usuario SMTP | Sí | - |
| `SMTP_PASS` | Contraseña SMTP (app password) | Sí | - |
| `NOTIFY_EMAIL` | Email destino de notificaciones | Sí | - |

## Consideraciones

- **Timeout**: 60 segundos para manejar cold start de Railway free tier (duerme tras 5min inactividad)
- **Reintentos**: 1 reintento automático si falla la conexión o timeout (importante para cold starts)
- **Logs**: Guardar salida en archivo para debug
- **Credenciales**: Solo en `.env`, nunca en el repo
