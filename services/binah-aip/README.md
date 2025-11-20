# Binah AIP (AI Platform)

> **📚 For detailed technical documentation, see [docs/services/binah-aip.md](../../docs/services/binah-aip.md)**

**Port:** 8090
**Tech Stack:** Python 3.11, FastAPI, PyTorch, TensorFlow, LangChain
**Purpose:** Unified AI/ML platform combining AI inference and LLM operations

## Overview

The Binah AI Platform (AIP) combines the functionality of two services:
- **AI Service** (`ai-service/`) - Machine learning models for predictions and analytics
- **LLM Service** (`llm-service/`) - Large language model operations for chat, reasoning, and embeddings

This unified platform provides all AI/ML capabilities for the Binelek real estate intelligence platform.

## Architecture

```
Binah AIP (8090)
├── AI Service
│   ├── Model Training
│   ├── Inference API
│   └── ML Pipelines
└── LLM Service
    ├── Chat/Completion
    ├── Embeddings
    └── Reasoning
```

## Features

### AI Service Features
- Property valuation prediction
- Risk assessment models
- Market trend analysis
- Custom ML model training
- Model versioning with MLflow

### LLM Service Features
- Natural language chat interface
- Document Q&A
- Semantic search with embeddings
- Multi-step reasoning
- Prompt engineering

## Running Locally

### Prerequisites
- Python 3.11+
- Ollama (for local LLM inference)
- MLflow server (optional, for model tracking)

### Development Mode

```bash
cd services/binah-aip

# Install dependencies
pip install -r ai-service/requirements.txt
pip install -r llm-service/requirements.txt

# Run AI Service
cd ai-service
uvicorn api.main:app --host 0.0.0.0 --port 8090 --reload

# Run LLM Service (in separate terminal)
cd llm-service
uvicorn api.main:app --host 0.0.0.0 --port 8091 --reload
```

## API Endpoints

### AI Service Endpoints (Port 8090)

```
POST   /api/ai/predict/cost         - Predict property costs
POST   /api/ai/predict/risk         - Assess investment risk
POST   /api/ai/train                - Train custom models
GET    /api/ai/models               - List available models
GET    /api/ai/models/{id}/status   - Get model status
```

### LLM Service Endpoints (Port 8091)

```
POST   /api/llm/chat                - Chat completion
POST   /api/llm/embeddings          - Generate embeddings
POST   /api/llm/reasoning           - Multi-step reasoning
GET    /api/llm/models              - List available LLMs
```

## Configuration

### Environment Variables

```bash
# AI Service
MLFLOW_TRACKING_URI=http://mlflow:5000
MODEL_STORAGE_PATH=/models
PYTORCH_DEVICE=cuda  # or 'cpu'

# LLM Service
OLLAMA_BASE_URL=http://ollama:11434
DEFAULT_LLM_MODEL=llama2
EMBEDDING_MODEL=nomic-embed-text
OPENAI_API_KEY=<optional>
```

## Models

### AI Models
- **Cost Prediction**: Random Forest / XGBoost models
- **Risk Assessment**: Neural network classifiers
- **Market Analysis**: Time series forecasting (LSTM)

### LLM Models (via Ollama)
- **llama2** - General chat and completion
- **mistral** - Fast inference
- **nomic-embed-text** - Embeddings generation

## Integration

### From Context Service
The Context Service forwards semantic objects to AIP for:
- Embedding generation
- Entity enrichment
- Semantic classification

### From Ontology Service
AIP can query the graph for:
- Feature engineering
- Training data collection
- Model validation

## Development

### Project Structure

```
binah-aip/
├── ai-service/
│   ├── api/              # FastAPI endpoints
│   ├── models/           # ML model definitions
│   ├── training/         # Training scripts
│   ├── inference/        # Inference logic
│   └── requirements.txt
├── llm-service/
│   ├── api/              # FastAPI endpoints
│   ├── embeddings/       # Embedding generation
│   ├── prompts/          # Prompt templates
│   ├── reasoning/        # Reasoning chains
│   └── requirements.txt
└── README.md
```

### Adding a New Model

1. Define model in `ai-service/models/`
2. Create training script in `ai-service/training/`
3. Register with MLflow
4. Add inference endpoint in `ai-service/api/`

## Monitoring

### MLflow
Track experiments, models, and metrics at `http://mlflow:5000`

### Health Checks
```
GET /health          # Service health
GET /health/models   # Model availability
```

## Related Services

- [binah-context](../binah-context/README.md) - Sends data for embedding
- [binah-ontology](../binah-ontology/README.md) - Graph queries for features

## License

Internal use only - Binelek Platform
