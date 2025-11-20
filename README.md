# binelek-ai

AI/ML services for machine learning and LLM operations

## Services Included

### 1. binah-aip (Port 8100)
AI Platform with 4 specialized agents, RAG, autonomous ontology (Python)

### 2. binah-ml (Port 8102)
ML training/inference, MLflow tracking (Python)

### 3. binah-regen (Code Generation)
Generates code from YAML ontology schemas (C#)

## Quick Start

```bash
git clone https://github.com/k5tuck/binelek-ai.git
cd binelek-ai
dotnet build
dotnet test
docker-compose up
```

## Dependencies

- **binelek-shared** - Shared libraries
- .NET 8.0 SDK / Python 3.11+
- Docker

## License

MIT License - See [LICENSE](LICENSE)
