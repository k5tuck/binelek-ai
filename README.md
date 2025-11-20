# binelek-ai

AI and ML services for the Binelek platform (Python)

## Services Included

### 1. binah-aip (Port 8100)
**Purpose:** AI Platform with intelligent agents and RAG capabilities

**Features:**
- 4 specialized AI agents (RAG Knowledge Base, Recommendation Engine, Predictive Analytics, Insight Generation)
- LangChain-based orchestration
- Vector search with Qdrant
- Neo4j knowledge graph integration
- Multi-tenant isolation

**Tech Stack:** Python 3.11+, FastAPI, LangChain, Qdrant, Neo4j

### 2. binah-ml (Port 8102)
**Purpose:** ML model training, inference, and experiment tracking

**Features:**
- Auto-training triggers at 100 entities
- 5 model types: price_prediction, risk_scoring, lead_scoring, churn_prediction, maintenance_prediction
- MLflow experiment tracking and model registry
- SHAP/LIME explainability
- Tenant-isolated model storage

**Tech Stack:** Python 3.11+, FastAPI, MLflow, scikit-learn, pandas, numpy

## Quick Start

### Prerequisites
- Python 3.11+
- pip or conda
- Docker & Docker Compose (for local services)

### Installation

```bash
# Clone repository
git clone https://github.com/k5tuck/binelek-ai.git
cd binelek-ai

# Install binah-aip dependencies
cd services/binah-aip
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install binah-ml dependencies
cd ../binah-ml
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running Services

**Option 1: Docker Compose** (recommended)
```bash
docker-compose up -d
```

**Option 2: Local Development**
```bash
# Run binah-aip
cd services/binah-aip
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8100

# Run binah-ml (in separate terminal)
cd services/binah-ml
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8102
```

### Testing

```bash
# Test binah-aip
cd services/binah-aip
pytest tests/

# Test binah-ml
cd services/binah-ml
pytest tests/
```

## API Documentation

Once services are running:
- **binah-aip:** http://localhost:8100/docs
- **binah-ml:** http://localhost:8102/docs

## Environment Variables

Both services require environment configuration. See:
- `services/binah-aip/.env.example`
- `services/binah-ml/.env.example`

Key variables:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` - Knowledge graph connection
- `QDRANT_URL` - Vector database connection
- `MLFLOW_TRACKING_URI` - ML experiment tracking
- `DATABASE_URL` - PostgreSQL connection
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` - LLM provider keys (optional, supports Ollama for local)

## Architecture

```
External Client
     ↓
binah-api (Gateway)
     ↓
┌────────────────────────┐
│   binah-aip (8100)    │
│  - RAG Agent          │
│  - Recommendation     │
│  - Predictive         │
│  - Insight            │
└────────────────────────┘
     ↓
┌────────────────────────┐
│   binah-ml (8102)     │
│  - Model Training     │
│  - Inference          │
│  - MLflow Tracking    │
└────────────────────────┘
     ↓
Data Sources (Neo4j, Qdrant, PostgreSQL)
```

## Development

### Code Style
- Follow PEP 8 guidelines
- Use Black for formatting: `black .`
- Use isort for imports: `isort .`
- Type hints required

### Adding New AI Agents (binah-aip)
1. Create agent class in `ai-service/agents/`
2. Register in `ai-service/orchestrator.py`
3. Add Kafka consumer if needed
4. Update tests

### Adding New ML Models (binah-ml)
1. Create model class in `app/models/`
2. Add training script in `app/training/`
3. Register in MLflow
4. Update API endpoints

## CI/CD

GitHub Actions workflows automatically:
- Run tests on all pull requests
- Check code style (Black, isort, flake8)
- Build Docker images
- Security scan (Bandit, Safety)

## Dependencies

### Shared Libraries
- **Binah.Contracts** - Event schemas, DTOs (consumed as Python dicts from Kafka)

### External Services
- **Neo4j** (2 instances) - Knowledge graph + Data Network
- **Qdrant** - Vector embeddings
- **PostgreSQL** - Relational data
- **Kafka** - Event streaming
- **MLflow** - ML tracking server

## Multi-Tenancy

Both services enforce strict tenant isolation:
- JWT authentication with tenant_id claim
- Tenant-specific model storage
- Tenant-filtered data queries
- Separate Qdrant collections per tenant

## Troubleshooting

### ImportError: No module named 'app'
```bash
# Ensure you're in the service directory and venv is activated
cd services/binah-aip  # or binah-ml
source venv/bin/activate
pip install -r requirements.txt
```

### Connection errors to Neo4j/Qdrant
```bash
# Check if services are running
docker-compose ps

# Restart services
docker-compose restart neo4j qdrant
```

### MLflow server not accessible
```bash
# Start MLflow server manually
mlflow server --host 0.0.0.0 --port 5000
```

## License

MIT License - See [LICENSE](LICENSE)

## Contributing

See main repository [CONTRIBUTING.md](https://github.com/k5tuck/Binelek/blob/main/CONTRIBUTING.md)

## Documentation

For detailed service documentation:
- **binah-aip:** See `services/binah-aip/README.md`
- **binah-ml:** See `services/binah-ml/README.md`

For platform architecture: [Binelek Platform Docs](https://github.com/k5tuck/Binelek/tree/main/docs)
