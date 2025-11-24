# binah-llm-extractor

**LLM-Powered Entity Extraction from Unstructured Data**

**Port:** 8110
**Status:** ✅ Ready to Deploy
**Version:** 1.0.0

---

## Overview

The **binah-llm-extractor** service extracts structured entities from unstructured text (emails, PDFs, documents, chat messages) using Large Language Models (LLMs). It integrates with `binah-discovery` to fetch ontology schemas, ensuring consistency between structured and unstructured data ingestion.

### Key Features

- ✅ **LLM-Powered Extraction** - Uses OpenAI GPT-4, Anthropic Claude, or Ollama Llama 3
- ✅ **Schema Integration** - Fetches schemas from binah-discovery for consistency
- ✅ **Confidence-Based Routing** - Auto-apply (≥90%), manual review (75-89%), reject (<75%)
- ✅ **Kafka Consumer** - Processes messages from `extraction.raw.*` topics
- ✅ **Multi-Provider Support** - OpenAI, Anthropic, or local Ollama
- ✅ **FastAPI REST API** - Manual extraction endpoint for testing

---

## Architecture

### Data Flow

```
Unstructured Text → binah-pipeline → Kafka (extraction.raw.{domain}.v1)
                                            ↓
                                   binah-llm-extractor
                                     - Fetches schema from binah-discovery
                                     - Extracts entities with LLM
                                     - Validates against schema
                                            ↓
                               ┌────────────┴────────────┐
                               ↓                         ↓
                         Confidence ≥ 90%         Confidence 75-89%
                         AUTO-CREATE              REVIEW QUEUE
                               ↓                         ↓
                        binah-ontology          binah-discovery
```

### Integration Points

| Service | Purpose |
|---------|---------|
| **binah-discovery** | Fetch ontology schemas, send to review queue |
| **binah-ontology** | Create validated entities in Neo4j |
| **binah-pipeline** | Source of unstructured data via Kafka |

---

## Installation

### Prerequisites

- Python 3.11+
- Kafka (for message consumption)
- binah-discovery (for schema fetching)
- binah-ontology (for entity creation)
- LLM API key (OpenAI, Anthropic, or local Ollama)

### Local Development

```bash
# Navigate to service directory
cd ai/services/binah-llm-extractor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
nano .env

# Run the service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8110 --reload
```

### Docker

```bash
# Build image
docker build -t binah-llm-extractor:latest .

# Run container
docker run -d \
  --name binah-llm-extractor \
  -p 8110:8110 \
  -e OPENAI_API_KEY=your-key \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e ONTOLOGY_SERVICE_URL=http://binah-ontology:8091 \
  -e DISCOVERY_SERVICE_URL=http://binah-discovery:8106 \
  binah-llm-extractor:latest
```

---

## Configuration

### Environment Variables

See `.env.example` for all configuration options.

**Key Settings:**

```bash
# LLM Provider
LLM_PROVIDER=openai  # openai, anthropic, or ollama
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_PATTERN=extraction.raw.*

# Service URLs
DISCOVERY_SERVICE_URL=http://binah-discovery:8106
ONTOLOGY_SERVICE_URL=http://binah-ontology:8091

# Confidence Thresholds (aligned with binah-discovery)
AUTO_APPLY_THRESHOLD=0.90
MANUAL_REVIEW_THRESHOLD=0.75
```

### LLM Providers

#### OpenAI (Default)

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4  # or gpt-3.5-turbo for lower cost
```

#### Anthropic Claude

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-sonnet-20241022
```

#### Ollama (Local, Free)

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3
```

---

## Usage

### Automatic Extraction (via Kafka)

The service automatically consumes messages from `extraction.raw.*` Kafka topics:

```bash
# Send unstructured text via binah-pipeline
POST /api/tenants/{tenant_id}/pipelines/{id}/execute
{
  "source": {"type": "Email", "folder": "Listings"},
  "destination": {
    "type": "Kafka",
    "topic": "extraction.raw.real_estate.v1"
  }
}

# binah-llm-extractor automatically:
# 1. Consumes message from extraction.raw.real_estate.v1
# 2. Fetches Property schema from binah-discovery
# 3. Extracts entities using LLM
# 4. Creates entities in binah-ontology (if confidence ≥ 90%)
# 5. Sends to review queue (if confidence 75-89%)
```

### Manual Extraction (REST API)

For testing or direct extraction:

```bash
POST http://localhost:8110/extract
{
  "text": "Property at 123 Main St, San Francisco, CA. 3 bed, 2 bath, 2400 sqft. Listed at $1.2M by John Smith (john@example.com).",
  "tenant_id": "tenant-abc",
  "domain": "real_estate"
}

# Response:
{
  "entities": [
    {
      "type": "Property",
      "attributes": {
        "address": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "bedrooms": 3,
        "bathrooms": 2,
        "squareFeet": 2400,
        "price": 1200000
      },
      "confidence": 0.95
    },
    {
      "type": "Owner",
      "attributes": {
        "name": "John Smith",
        "email": "john@example.com"
      },
      "confidence": 0.92
    }
  ],
  "count": 2
}
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Service statistics |
| `/extract` | POST | Manual entity extraction |
| `/docs` | GET | OpenAPI documentation |

---

## Example Workflow

### Scenario: Extract Property from Email

```bash
# 1. Email arrives with listing
Subject: New Listing - 123 Main St
Body: Great property! 3 bed, 2 bath, 2400 sqft in San Francisco.
      $1.2M. Contact John at john@example.com

# 2. binah-pipeline ingests email
POST /api/tenants/realestate-co/pipelines/email-ingest/execute

# 3. Pipeline publishes to Kafka
Topic: extraction.raw.real_estate.v1
Message: {
  "tenant_id": "realestate-co",
  "text": "Great property! 3 bed, 2 bath, 2400 sqft...",
  "metadata": {"subject": "New Listing - 123 Main St"}
}

# 4. binah-llm-extractor consumes message
# - Fetches Property schema from binah-discovery
# - Calls GPT-4 to extract entity
# - Validates against schema
# - Confidence: 0.95 (≥ 90% threshold)

# 5. Entity auto-created in binah-ontology
POST /api/tenants/realestate-co/entities
{
  "entityType": "Property",
  "attributes": {
    "address": "123 Main St",
    "city": "San Francisco",
    "bedrooms": 3,
    "bathrooms": 2,
    "squareFeet": 2400,
    "price": 1200000
  }
}

# 6. Property now queryable in Neo4j!
MATCH (p:Property {address: "123 Main St"}) RETURN p
```

---

## How It Works with binah-discovery

### Schema Synchronization

```python
# 1. binah-discovery auto-generates schema from CSV
CSV: address,price,bedrooms,bathrooms
     "123 Main St",1200000,3,2.5
     ↓
binah-discovery creates ontology:
entities:
  - name: Property
    attributes:
      - name: address
        type: string
      - name: price
        type: money
      - name: bedrooms
        type: int

# 2. binah-llm-extractor fetches same schema
GET /api/ontology/{tenant_id}/current
Response: {same ontology as above}

# 3. LLM extraction uses EXACT same schema
System Prompt: "Extract entities matching this schema: ..."
User Prompt: "Property at 456 Oak Ave..."
LLM Response: {
  "type": "Property",
  "attributes": {
    "address": "456 Oak Ave",  # Same schema!
    "price": 850000,
    "bedrooms": 4
  }
}
```

### Confidence Thresholds (Aligned)

Both services use the same thresholds:

| Confidence | binah-discovery | binah-llm-extractor |
|-----------|----------------|---------------------|
| ≥ 90% | Auto-apply | Auto-create entity |
| 75-89% | Manual review | Send to review queue |
| < 75% | Reject | Reject |

---

## Monitoring

### Health Check

```bash
curl http://localhost:8110/health

{
  "status": "healthy",
  "service": "binah-llm-extractor",
  "version": "1.0.0",
  "provider": "openai",
  "model": "gpt-4"
}
```

### Service Stats

```bash
curl http://localhost:8110/stats

{
  "service": "binah-llm-extractor",
  "version": "1.0.0",
  "kafka_connected": true,
  "kafka_topic_pattern": "extraction.raw.*",
  "provider": "openai",
  "model": "gpt-4",
  "confidence_thresholds": {
    "auto_apply": 0.9,
    "manual_review": 0.75
  }
}
```

### Logs

```bash
# View logs in Docker
docker logs -f binah-llm-extractor

# Sample log output
2025-11-24 10:30:00 - INFO - Kafka consumer started successfully
2025-11-24 10:30:15 - INFO - Processing message from topic=extraction.raw.real_estate.v1
2025-11-24 10:30:16 - INFO - Fetched ontology schema for tenant=tenant-abc: 5 entities
2025-11-24 10:30:18 - INFO - Extracted 2 entities from message
2025-11-24 10:30:19 - INFO - ✓ Created entity: Property with ID abc-123 (confidence: 0.95)
```

---

## Cost Optimization

### Tips for Reducing LLM API Costs

1. **Use GPT-3.5 for Simple Extractions** - $0.001/1K tokens vs $0.03/1K for GPT-4
2. **Use Ollama for Development** - Free local models (Llama 3)
3. **Batch Processing** - Process multiple texts in one LLM call (future feature)
4. **Confidence Thresholds** - Reject low-quality data early
5. **Structured Data First** - Use binah-discovery for CSV/JSON (no LLM cost)

### Cost Comparison

| LLM Provider | Model | Cost per 1K tokens | Use Case |
|--------------|-------|-------------------|----------|
| OpenAI | GPT-4 | $0.03 input / $0.06 output | Complex extraction, high accuracy |
| OpenAI | GPT-3.5-turbo | $0.001 / $0.002 | Simple extraction, cost-sensitive |
| Anthropic | Claude 3.5 Sonnet | $0.003 / $0.015 | High quality, reasonable cost |
| Ollama | Llama 3 | **Free** | Development, privacy-sensitive |

---

## Troubleshooting

### Common Issues

**1. "No ontology schema found"**
```
Solution: Create schema first using binah-discovery with structured data (CSV/JSON)
```

**2. "LLM API call failed"**
```
Check: API key is valid, rate limits not exceeded
```

**3. "Kafka consumer not connecting"**
```
Check: KAFKA_BOOTSTRAP_SERVERS is correct, topic exists
```

**4. "Low extraction quality"**
```
Solution: Use GPT-4 instead of GPT-3.5, adjust temperature lower (0.1)
```

---

## Development

### Project Structure

```
binah-llm-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration settings
│   ├── extractor.py     # LLM entity extraction logic
│   └── consumer.py      # Kafka consumer
├── Dockerfile
├── requirements.txt
├── .env.example
├── .dockerignore
└── README.md
```

### Running Tests

```bash
# TODO: Add tests
pytest tests/
```

---

## Deployment

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
binah-llm-extractor:
  build:
    context: ./ai/services/binah-llm-extractor
  container_name: binah-llm-extractor
  ports:
    - "8110:8110"
  environment:
    LLM_PROVIDER: openai
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    ONTOLOGY_SERVICE_URL: http://binah-ontology:8091
    DISCOVERY_SERVICE_URL: http://binah-discovery:8106
    AUTO_APPLY_THRESHOLD: 0.90
    MANUAL_REVIEW_THRESHOLD: 0.75
  depends_on:
    kafka:
      condition: service_healthy
    binah-ontology:
      condition: service_healthy
    binah-discovery:
      condition: service_healthy
  networks:
    - binelek-network
  restart: unless-stopped
```

---

## Related Services

- **binah-discovery** - Auto-discovers schemas from structured data (CSV, JSON, SQL)
- **binah-ontology** - Manages entities and knowledge graph (Neo4j)
- **binah-pipeline** - Data ingestion from multiple sources
- **binah-aip** - AI agent orchestration

---

## License

Part of the Binelek Platform

---

## Support

For issues or questions:
- Check logs: `docker logs binah-llm-extractor`
- Review API docs: `http://localhost:8110/docs`
- See LLM_ENTITY_EXTRACTION_GUIDE.md in project root

---

**Ready to extract entities from unstructured data! 🚀**
