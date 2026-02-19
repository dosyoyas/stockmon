# Plan: StockMon API

## Contexto

API REST para monitoreo de acciones. Recibe tickers con umbrales de compra/venta, consulta datos de las últimas 24h vía YFinance, y devuelve alertas cuando los precios han cruzado los umbrales. Diseñada para ser stateless y sin datos sensibles, desplegada en Railway.

## Stack

- **Python 3.11+**
- **FastAPI** - Framework web
- **YFinance** - Datos de mercado
- **Uvicorn** - Servidor ASGI
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **httpx** - Test client for FastAPI

## Estructura de archivos

```
stockmon/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, endpoints
│   ├── models.py        # Pydantic schemas
│   ├── auth.py          # Validación API key
│   └── services/
│       ├── __init__.py
│       └── stock.py     # Lógica YFinance
├── client/
│   ├── __init__.py
│   ├── main.py          # Script principal
│   ├── config.json      # Tickers y umbrales
│   └── notified.json    # Alertas ya notificadas (auto-generado)
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # Fixtures (mock YFinance, test client)
│   ├── test_auth.py     # Auth validation tests
│   ├── test_alerts.py   # Alert logic tests
│   ├── test_stock.py    # YFinance service tests
│   └── test_client.py   # Client tests
├── requirements.txt
├── requirements-dev.txt # Dev/test dependencies
├── Procfile             # Railway deployment
├── .env.example         # Ejemplo de variables de entorno
└── .gitignore
```

## Endpoint principal

```
POST /check-alerts
```

**Request:**
```json
{
  "AAPL": {"buy": 170, "sell": 190},
  "MSFT": {"buy": 400, "sell": 420}
}
```

**Response:**
```json
{
  "alerts": [
    {
      "ticker": "AAPL",
      "type": "buy",
      "threshold": 170,
      "reached": 168.50,
      "current": 172.30
    }
  ],
  "errors": [
    {"ticker": "INVALID", "error": "Ticker not found"}
  ],
  "market_open": true,
  "service_degraded": false,
  "checked_at": "2024-02-06T14:30:00Z"
}
```

**Nota**: `service_degraded: true` indica que YFinance falló para todos los tickers (probable rotura de la librería). El cliente debe alertar al usuario.

## Lógica de alertas

Para cada ticker:
1. Obtener datos de las últimas 24h (intervalo **1 hora**)
2. Calcular min/max del período
3. Si `min <= buy_threshold` → alerta tipo "buy"
4. Si `max >= sell_threshold` → alerta tipo "sell"

**Manejo de errores**: Respuesta parcial. Si un ticker falla, se incluye en lista de errores pero no afecta a los demás.

**Mercado cerrado**: Si el mercado está cerrado (fines de semana, festivos, fuera de horario NYSE), la API devuelve `alerts: []` y un campo `market_open: false` para que el cliente sepa que no hay datos nuevos.

**Doble alerta**: Si un ticker cruza ambos umbrales (muy volátil), se devuelven ambas alertas (buy y sell) con sus respectivos valores alcanzados.

**Fallo de YFinance**: Si todos los tickers fallan (probable rotura de YFinance por cambios en Yahoo), la respuesta incluye `service_degraded: true`. El cliente debe notificar al usuario para que actualice las librerías.

## Autenticación

API key simple vía header:

```
X-API-Key: tu-clave-secreta
```

- La API key se configura como variable de entorno `API_KEY` en el servidor
- Todos los endpoints excepto `/health` requieren autenticación
- Respuesta 401 si falta o es inválida

**Implementación**: Dependency de FastAPI que valida el header en cada request.

## Endpoints adicionales

- `GET /health` - Health check para el hosting (sin auth)
- `GET /` - Info básica de la API

## Implementación

### 1. Crear estructura base
- `requirements.txt` con dependencias
- `app/main.py` con FastAPI app

### 2. Definir modelos Pydantic
- `TickerThresholds` - Input por ticker
- `Alert` - Alerta individual
- `CheckAlertsResponse` - Response completo

### 3. Servicio de stocks
- Función para obtener min/max 24h de un ticker
- Timeout de **10 segundos** por ticker (si excede, va a lista de errores)
- Manejo de errores (ticker inválido, mercado cerrado)

### 4. Endpoint /check-alerts
- Validar input (máximo **20 tickers** por request)
- Umbrales `buy` y `sell` son **opcionales** (puede enviar uno o ambos)
- Iterar tickers, consultar YFinance
- Generar alertas según umbrales

### 5. Configuración de despliegue
- `Procfile` para Railway
- Variables de entorno en Railway dashboard

## Verificación

1. **Local**: `uvicorn app.main:app --reload`
2. **Test manual**:
   ```bash
   curl -X POST http://localhost:8000/check-alerts \
     -H "Content-Type: application/json" \
     -H "X-API-Key: tu-clave-secreta" \
     -d '{"AAPL": {"buy": 170, "sell": 250}}'
   ```
3. **Swagger UI**: http://localhost:8000/docs

## Testing

### Estrategia

Mockear YFinance para tests determinísticos. Nunca llamar a Yahoo en tests.

### Fixtures (conftest.py)

```python
@pytest.fixture
def mock_yfinance(monkeypatch):
    """Mock yfinance.Ticker para retornar datos controlados"""
    # Retorna DataFrame con datos predefinidos

@pytest.fixture
def client():
    """FastAPI TestClient con API key válida"""

@pytest.fixture
def client_no_auth():
    """FastAPI TestClient sin API key"""
```

### Test cases

**test_auth.py:**
- Request sin header `X-API-Key` → 401
- Request con API key inválida → 401
- Request con API key válida → 200
- Endpoint `/health` sin auth → 200

**test_alerts.py:**
- Ticker con precio bajo umbral buy → alerta buy
- Ticker con precio sobre umbral sell → alerta sell
- Ticker muy volátil → ambas alertas (buy y sell)
- Ticker sin cruzar umbrales → sin alertas
- Solo umbral buy definido → ignora sell
- Solo umbral sell definido → ignora buy
- Más de 20 tickers → 422 validation error

**test_stock.py:**
- Ticker válido → retorna min/max
- Ticker inválido → retorna error en lista de errores
- Timeout de YFinance → error graceful
- Mercado cerrado → `market_open: false`
- Todos los tickers fallan → `service_degraded: true`

### Ejecución

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=app --cov-report=term-missing

# Solo un archivo
pytest tests/test_alerts.py -v
```

## Development Setup

### Requisitos previos
- Python 3.11+
- pip

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/dosyoyas/stockmon.git
cd stockmon

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para desarrollo/tests

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu API_KEY
```

### Ejecutar localmente

```bash
# Servidor de desarrollo
uvicorn app.main:app --reload

# API disponible en http://localhost:8000
# Swagger UI en http://localhost:8000/docs
```

### Ejecutar tests

```bash
pytest
pytest --cov=app --cov-report=term-missing
```

## Variables de entorno

| Variable | Descripción | Requerida | Default |
|----------|-------------|-----------|---------|
| `API_KEY` | Clave para autenticar requests | Sí | - |
| `PORT` | Puerto del servidor (Railway lo configura) | No | 8000 |

## Despliegue en Railway

### Procfile

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Pasos

1. Crear proyecto en Railway
2. Conectar repositorio `dosyoyas/stockmon` de GitHub
3. Configurar variables de entorno en Railway dashboard:
   - `API_KEY`: Tu clave secreta
4. Deploy automático en cada push a main

### Verificar despliegue

```bash
curl https://tu-app.railway.app/health
```

## Consideraciones

- **Rate limiting**: Añadir `slowapi` si hay abuso
- **Caché**: Opcional, cachear respuestas YFinance por 5min
- **Cold start**: Railway free tier duerme tras 5min inactividad. Cliente usa timeout de 60s para manejar wake-up.
- **Límites free tier**: Railway free tier tiene 500 horas/mes. El cron cada 15min mantendrá la app despierta ~8h/día si hay actividad continua.
- **YFinance no oficial**: Riesgo a largo plazo si Yahoo cambia su web. Sin acción inmediata.
