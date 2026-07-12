# Redacting Telemetry with Presidio

**A practical example of redacting PII in logs using Presidio.**

> ⚠️ This is a proof-of-concept demonstration, not a production-ready solution.

## What This Demo Shows

This sample demonstrates **client-side PII masking** before logs are exported to observability platforms like Grafana/Loki. The application calls Presidio to detect and mask PII (names, emails, SSNs, phone numbers) before logging.

## Considerations and Out of Scope

This demo intentionally does NOT cover:

- Production deployment patterns
- Configurations, NLP model selection, or custom entity recognizers
- Reliability & Performance optimization
- Alternative architectures (sidecar, (otel-)collector-side masking, et cetera)

**Architecture:**

```
Application → Presidio (mask PII) → OpenTelemetry Collector → Loki/Tempo → Grafana
```

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Run the Demo

```bash
cd docs/samples/deployments/redacting-telemetry
docker compose up -d

# Wait ~60 seconds for Presidio to download models
# Then open Grafana
```

**Access Grafana:** http://localhost:3000

Navigate to **Dashboards → PII Redaction Demo** to see:

- **Unredacted Logs Panel**: Raw PII (names, emails, SSNs)
- **Redacted Logs Panel**: PII replaced with types (`<PERSON>`, `<EMAIL_ADDRESS>`, `<US_SSN>`)

The dashboard auto-refreshes every 5 seconds.

## What's Running

| Service                 | Purpose                         | Port       |
| ----------------------- | ------------------------------- | ---------- |
| **presidio-analyzer**   | Detects PII using NLP           | 5002       |
| **presidio-anonymizer** | Masks detected PII              | 5001       |
| **pii-demo-app**        | FastAPI app generating PII logs | 8000       |
| **otel-collector**      | Receives and forwards telemetry | 4317, 4318 |
| **loki**                | Log aggregation                 | 3100       |
| **tempo**               | Distributed tracing             | 3200       |
| **grafana**             | Visualization                   | 3000       |

## How It Works

The demo app (`app/main.py`) generates logs with PII, then calls Presidio to mask them:

```python
from presidio_client import mask_pii

# Original log
unredacted = "User registered: John Doe, SSN: 123-45-6789, Email: john@example.com"
logger.info(f"[UNREDACTED] {unredacted}")

# Redacted log
redacted = mask_pii(unredacted)  # Calls Presidio
logger.info(f"[REDACTED] {redacted}")
# Output: [REDACTED] User registered: <PERSON>, SSN: <US_SSN>, Email: <EMAIL_ADDRESS>
```

The `presidio_client.py` makes two HTTP calls:

1. **Analyze**: Detect PII entities
2. **Anonymize**: Replace with placeholders

## Use in Your Application

### Python Example

Copy `app/presidio_client.py` to your project:

```python
from presidio_client import mask_pii

# Before logging sensitive data
sensitive = f"Customer {name} called from {phone}"
redacted = mask_pii(sensitive)
logger.info(redacted)  # "Customer <PERSON> called from <PHONE_NUMBER>"
```

## Cleanup

```bash
docker compose down       # Stop services
docker compose down -v    # Stop and delete data
```

