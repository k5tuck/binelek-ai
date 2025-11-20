# Binah ML - Machine Learning Training and Inference Pipeline

> **📚 For detailed technical documentation, see [docs/services/binah-ml.md](../../docs/services/binah-ml.md)**

ML service with MLFlow integration for model training, experiment tracking, and inference - **JWT Secured with Multi-Tenant Isolation**.

**Version:** 0.2.0
**Status:** ✅ Production Ready (Phase 1 Week 1 Complete)
**Security:** JWT Authentication + Tenant Isolation Enforced

## Overview

Binah ML provides end-to-end machine learning capabilities for real estate analytics:
- ✅ **JWT Authentication** - All ML endpoints secured with token validation
- ✅ **Tenant Isolation** - Complete data segregation per tenant
- ✅ **Model Training** - Automated experiment tracking with MLFlow
- ✅ **Model Registry** - Versioning and lifecycle management
- ✅ **Inference API** - Real-time predictions with trained models
- ✅ **Multi-Model Support** - 4 ML model types for real estate analytics

## Supported Models

### 1. Cost Forecasting (XGBoost Regression)
Predicts total project costs based on:
- Project size (sqft)
- Number of units
- Location tier
- Property type
- Year

**Metrics:** RMSE, MAE, R²

### 2. Risk Assessment (Random Forest Classification)
Assesses investment risk based on:
- Leverage ratio
- Occupancy rate
- Market volatility
- Property age
- Location risk score

**Metrics:** Accuracy, AUC-ROC

### 3. ROI Prediction (XGBoost Regression)
Predicts return on investment using:
- Purchase price
- Annual revenue
- Operating expenses
- Property type
- Market growth rate

**Metrics:** RMSE, MAE, R²

### 4. Anomaly Detection (Isolation Forest)
Detects anomalies in property metrics:
- Monthly revenue
- Occupancy rate
- Maintenance costs
- Tenant turnover

**Metrics:** Anomaly rate, Count

## Authentication & Security

### JWT Authentication

**ALL ML endpoints require a valid JWT token** from the binah-auth service.

#### Required JWT Claims:
- `sub` - User ID (from authentication service)
- `tenant_id` - Tenant identifier (snake_case format)
- `email` - User email
- `role` - User role (admin, user, etc.)
- `exp` - Token expiration timestamp
- `iss` - Issuer (must be "Binah.Auth")
- `aud` - Audience (must be "Binah.Platform")

#### Authentication Flow:
1. User authenticates with **binah-auth** service
2. Receives JWT token with tenant_id claim
3. Includes token in requests to binah-ml: `Authorization: Bearer <token>`
4. binah-ml validates token signature, expiration, issuer, and audience
5. Extracts tenant_id from JWT (source of truth)
6. Validates request tenant_id matches JWT tenant_id
7. Sets tenant context for request processing

### Tenant Isolation

**Complete tenant isolation enforced at all layers:**

#### Layer 1: Authentication
- JWT token validation on every request
- Tenant ID extracted from validated token claims
- Invalid/expired tokens rejected (401 Unauthorized)

#### Layer 2: Request Validation
- Request body tenant_id compared against JWT tenant_id
- Mismatched tenant_id rejected (403 Forbidden)
- Cross-tenant access attempts logged and blocked

#### Layer 3: Business Logic
- Tenant context set per-request using ContextVar
- Automatic context cleanup after request
- All operations scoped to authenticated tenant

#### Layer 4: Data Access (Future)
- All database queries filtered by tenant_id
- Row-level security policies
- Tenant-tagged MLFlow experiments

### Security Testing

**100% Test Pass Rate - 19 Security Tests:**
- ✅ 12 Authentication Tests (Day 2)
- ✅ 7 Tenant Isolation Tests (Day 3)

See [docs/PHASE_1_DAY_2_TEST_RESULTS.md](../../docs/PHASE_1_DAY_2_TEST_RESULTS.md) and [docs/PHASE_1_DAY_3_SUMMARY.md](../../docs/PHASE_1_DAY_3_SUMMARY.md) for detailed test results.

## Installation

### Prerequisites

- Python 3.11+
- MLFlow server (or embedded)
- Neo4j and PostgreSQL (for training data)
- **JWT Secret Key** (shared with binah-auth service)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

**Required Environment Variables:**
```env
# JWT Authentication (REQUIRED)
JWT_SECRET=your-secure-secret-key-min-32-characters  # MUST match binah-auth
JWT_ISSUER=Binah.Auth
JWT_AUDIENCE=Binah.Platform
JWT_ALGORITHM=HS256

# Server
API_HOST=0.0.0.0
API_PORT=8098
ENVIRONMENT=development  # or production

# MLFlow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=binelek-ml

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=binah_ml
POSTGRES_USER=binah
POSTGRES_PASSWORD=your_password

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Security
ENABLE_TENANT_ISOLATION=true
```

**⚠️ CRITICAL for Production:**
- Set `JWT_SECRET` to a strong random key (min 32 characters)
- MUST match the secret used by binah-auth service
- Never commit `.env` file to version control
- Use environment variables or secrets manager in production

3. Start MLFlow server:
```bash
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0 \
  --port 5000
```

4. Run the service:
```bash
python -m app.main
# or with auto-reload:
uvicorn app.main:app --host 0.0.0.0 --port 8098 --reload
```

## API Endpoints

**🔒 All `/api/ml/*` endpoints require JWT authentication.**

### Authentication Test Endpoint

**GET /me** 🔒 **Protected**

Test your JWT authentication and view decoded token claims.

**Headers:**
```
Authorization: Bearer <your_jwt_token>
```

**Response (200 OK):**
```json
{
  "user_id": "test-user-123",
  "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "email": "user@example.com",
  "role": "admin",
  "message": "Authentication successful"
}
```

**Error Responses:**
- `403 Forbidden` - No token provided
- `401 Unauthorized` - Invalid, expired, or malformed token

### Train Model

**POST /api/ml/train** 🔒 **Protected**

Train a new model with MLFlow experiment tracking.

**Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "model_type": "cost_forecasting",
  "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "hyperparameters": {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1
  },
  "validation_split": 0.2
}
```

**⚠️ Security:** `tenant_id` in request body MUST match `tenant_id` in JWT token. Mismatches result in 403 Forbidden.

**Response (200 OK):**
```json
{
  "run_id": "abc123def456",
  "model_type": "cost_forecasting",
  "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "status": "completed",
  "metrics": {
    "rmse": 125432.50,
    "mae": 98234.12,
    "r2": 0.87
  },
  "model_uri": "runs:/abc123def456/model",
  "message": "Model trained successfully"
}
```

**Error Responses:**
- `403 Forbidden` - No token or tenant_id mismatch
- `401 Unauthorized` - Invalid/expired token
- `500 Internal Server Error` - Training failed

**Example with curl:**
```bash
# Get JWT token from binah-auth first
TOKEN="your_jwt_token_here"

# Train model
curl -X POST http://localhost:8098/api/ml/train \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "cost_forecasting",
    "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "validation_split": 0.2
  }'
```

### Make Prediction

**POST /api/ml/predict** 🔒 **Protected**

Make predictions using trained models.

**Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "model_type": "roi_prediction",
  "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "features": {
    "purchase_price": 1500000,
    "annual_revenue": 180000,
    "operating_expenses": 72000,
    "property_type": 2,
    "market_growth_rate": 0.05
  },
  "model_version": "v1.0"
}
```

**⚠️ Security:** `tenant_id` in request body MUST match `tenant_id` in JWT token.

**Response (200 OK):**
```json
{
  "model_type": "roi_prediction",
  "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "prediction": {
    "value": 0.85,
    "note": "Demo prediction - model not yet trained"
  },
  "confidence": 0.92,
  "model_version": "v1.0"
}
```

**Error Responses:**
- `403 Forbidden` - No token or tenant_id mismatch
- `401 Unauthorized` - Invalid/expired token
- `500 Internal Server Error` - Prediction failed

### Health Check Endpoints

**GET /** ✅ **Public** (No authentication required)

Service information endpoint.

**Response (200 OK):**
```json
{
  "service": "Binah ML",
  "version": "0.2.0",
  "description": "Machine Learning training and inference with MLFlow - JWT Secured",
  "status": "operational",
  "authentication": "required",
  "docs": "/docs"
}
```

**GET /health** ✅ **Public** (No authentication required)

Health check endpoint for Kubernetes liveness/readiness probes.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "binah-ml",
  "version": "0.2.0",
  "mlflow_uri": "http://localhost:5000",
  "database": "binah_ml",
  "tenant_isolation_enabled": true,
  "authentication_enabled": true
}
```

**GET /api/ml/health** 🔒 **Protected**

ML router health check - requires authentication.

**Headers:**
```
Authorization: Bearer <your_jwt_token>
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "binah-ml",
  "router": "/api/ml",
  "authenticated_tenant": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "authentication": "enabled"
}
```

## MLFlow Integration

### Experiment Tracking

All training runs are automatically logged to MLFlow:
- **Parameters:** Model type, hyperparameters, tenant ID
- **Metrics:** RMSE, MAE, R², Accuracy, AUC-ROC
- **Artifacts:** Trained model files
- **Tags:** Tenant ID, model type, status

### View Experiments

Access MLFlow UI:
```
http://localhost:5000
```

### Model Registry

Models are versioned and registered:
```python
import mlflow

# Load model by run ID
model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")

# Or by model name and version
model = mlflow.pyfunc.load_model("models:/cost_forecasting/1")
```

## Training Data

Training data is loaded from:
- **Neo4j:** Property attributes, relationships
- **PostgreSQL:** Pipeline data, financial records

Custom queries can be provided via `training_data_query` parameter.

## Hyperparameter Tuning

Example hyperparameters for each model:

**XGBoost (Cost Forecasting, ROI Prediction):**
```json
{
  "n_estimators": 100,
  "max_depth": 6,
  "learning_rate": 0.1,
  "subsample": 0.8,
  "colsample_bytree": 0.8
}
```

**Random Forest (Risk Assessment):**
```json
{
  "n_estimators": 100,
  "max_depth": 10,
  "min_samples_split": 5,
  "min_samples_leaf": 2
}
```

**Isolation Forest (Anomaly Detection):**
```json
{
  "n_estimators": 100,
  "contamination": 0.05,
  "max_samples": 256
}
```

## Automated Retraining

Configure automatic model retraining:

```env
AUTO_RETRAIN=true
RETRAIN_SCHEDULE=0 2 * * *  # Daily at 2 AM
```

## Development

### Project Structure

```
binah-ml/
├── app/
│   ├── models.py          # Pydantic models
│   ├── config.py          # Configuration
│   ├── main.py            # FastAPI app
│   ├── training/
│   │   └── pipeline.py    # MLFlow training pipeline
│   ├── inference/         # Model inference
│   └── routers/
│       └── ml.py          # API routes
├── notebooks/             # Jupyter notebooks for experiments
├── data/                  # Training data
├── mlruns/               # MLFlow artifacts
├── requirements.txt
└── README.md
```

### Adding New Models

1. Add model type to `models.py`
2. Implement training logic in `pipeline.py`
3. Add hyperparameters and metrics
4. Register in MLFlow

## Testing Authentication

### Generate Test JWT Token

Use the provided test token generator:

```bash
cd /home/user/Binelek/services/binah-ml
python3 test_jwt_generator.py
```

This generates test tokens for:
- Normal admin user (tenant A)
- Different tenant user (tenant B)
- Non-admin user
- Expired token

### Test Authentication Flow

```bash
# 1. Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8098

# 2. Generate test token
python3 test_jwt_generator.py

# 3. Test unauthenticated access (should fail)
curl http://localhost:8098/api/ml/health
# Expected: 403 Forbidden

# 4. Test with valid token
TOKEN="your_generated_token"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8098/me
# Expected: 200 OK with user info

# 5. Test cross-tenant access (should fail)
TENANT_B_TOKEN="different_tenant_token"
curl -X POST http://localhost:8098/api/ml/predict \
  -H "Authorization: Bearer $TENANT_B_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_type": "cost_forecasting", "tenant_id": "tenant-a-uuid", "features": {}}'
# Expected: 403 Forbidden (tenant mismatch)
```

### Run Security Test Suite

```bash
# Run all authentication tests (12 tests)
python3 test_authentication.py
# Expected: 12/12 PASSED

# Run all tenant isolation tests (7 tests)
python3 test_tenant_isolation.py
# Expected: 7/7 PASSED
```

## Production Deployment

### Security Checklist

**CRITICAL - Before deploying to production:**

- [ ] Set strong `JWT_SECRET` environment variable (min 32 characters)
- [ ] Ensure `JWT_SECRET` matches binah-auth service
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `POSTGRES_PASSWORD` and `NEO4J_PASSWORD`
- [ ] Update CORS allowed origins in `main.py` (remove localhost, add production domains)
- [ ] Enable HTTPS via reverse proxy (nginx, API gateway)
- [ ] Set up secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Configure log aggregation (CloudWatch, ELK, etc.)
- [ ] Set up monitoring and alerts
- [ ] Review and test rollback plan

See [docs/PHASE_1_SECURITY_AUDIT_CHECKLIST.md](../../docs/PHASE_1_SECURITY_AUDIT_CHECKLIST.md) for complete security audit results.

### Docker

```bash
# Build
docker build -t binah-ml .

# Run with environment file
docker run -p 8098:8098 -p 5000:5000 --env-file .env binah-ml
```

**Production Docker Run:**
```bash
docker run -d \
  --name binah-ml \
  -p 8098:8098 \
  -p 5000:5000 \
  -e ENVIRONMENT=production \
  -e JWT_SECRET=${JWT_SECRET} \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  -e NEO4J_PASSWORD=${NEO4J_PASSWORD} \
  -v /app/mlruns:/app/mlruns \
  -v /app/models:/app/models \
  binah-ml:latest
```

### Model Serving

For production inference, consider:
- MLFlow Model Serving
- TensorFlow Serving
- TorchServe
- Custom FastAPI inference service

## Monitoring

### Model Performance

Track model drift and performance:
- Monitor prediction accuracy over time
- Compare training vs production metrics
- Set up alerts for degraded performance

### MLFlow Metrics

Key metrics to monitor:
- Training time
- Model size
- Inference latency
- Resource usage

## Roadmap

- [ ] Hyperparameter optimization (Optuna, Ray Tune)
- [ ] Model ensembles
- [ ] A/B testing framework
- [ ] Feature engineering pipeline
- [ ] Model explainability (SHAP values)
- [ ] Online learning for real-time updates

## License

Proprietary - Binah Platform
