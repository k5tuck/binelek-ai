# Autonomous Ontology Management - Quick Start Guide

Get started with the autonomous ontology management system in 5 minutes!

---

## What is This?

An **AI-powered system that automatically improves your ontology** by:
- 📊 Monitoring how users query your knowledge graph
- 🤖 Using LLMs to suggest improvements (new relationships, indexes, etc.)
- 🧪 Simulating changes before deployment (future)
- ✅ Getting human approval for changes (future)
- 🚀 Automatically deploying improvements (future)

**Current Status:** Phase 1-2 Implemented (Data Collection + AI Recommendations)

---

## Quick Start (5 Minutes)

### 1. Set Environment Variables

Create `services/binah-aip/.env`:

```bash
# Choose your LLM provider
LLM_PROVIDER=openai  # or 'anthropic' or 'ollama'

# If using OpenAI:
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4-turbo

# Service config
API_PORT=8096
```

### 2. Install Dependencies

```bash
cd services/binah-aip
pip install fastapi uvicorn langchain langchain-openai pydantic
```

### 3. Start the Service

```bash
python -m app.main
```

You should see:
```
INFO:     Initializing Binah AIP service...
INFO:     Initialized OpenAI LLM: gpt-4-turbo
INFO:     AI Orchestrator initialized
INFO:     Autonomous Ontology Orchestrator initialized
INFO:     Binah AIP service started successfully on 0.0.0.0:8096
```

### 4. Generate Recommendations

```bash
curl -X POST http://localhost:8096/api/autonomous-ontology/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-tenant",
    "domain": "real-estate",
    "time_window_days": 30,
    "min_priority": "low"
  }'
```

**Expected Output:**
```json
{
  "recommendations": [
    {
      "id": "rec-demo-tenant-...",
      "type": "new_relationship",
      "priority": "high",
      "title": "Add direct Property → Transaction relationship",
      "rationale": "Queries frequently traverse Property → Owner → Transaction...",
      "impact": "Expected 40% performance improvement...",
      "predicted_improvement": 40.0
    }
  ],
  "total_count": 5,
  "generated_at": "2025-11-13T..."
}
```

---

## What Just Happened?

The system:

1. **Collected Mock Metrics** (since no real database connected)
   - Entity access patterns
   - Relationship traversals
   - Query patterns

2. **Aggregated Insights**
   - Top accessed entities
   - Slow queries
   - Co-accessed entities (for relationship suggestions)
   - Data quality issues

3. **Asked the LLM** (GPT-4)
   - "Given these usage patterns, how can we improve the ontology?"
   - LLM analyzed patterns and generated recommendations

4. **Returned Structured Recommendations**
   - Each with rationale, impact, risk assessment
   - Prioritized by impact and risk

---

## Example Recommendation Types

### 1. New Relationship
```
Property → Owner → Transaction (2 hops, slow)
   ↓
Suggestion: Add direct Property → Transaction relationship
Expected: 40% faster queries
```

### 2. Computed Field
```
Every query calculates: age = TODAY() - date_of_birth
   ↓
Suggestion: Add "age" as computed field
Expected: Eliminate redundant calculations
```

### 3. Index Optimization
```
95% of Client queries filter by email + company_id
   ↓
Suggestion: Add composite index on (email, company_id)
Expected: 60% faster lookups
```

### 4. Validation Rule
```
30% of phone numbers have invalid format
   ↓
Suggestion: Add regex validation pattern
Expected: Improved data quality
```

### 5. Entity Consolidation
```
"Client" and "Contact" entities 80% overlap
   ↓
Suggestion: Merge into single "Client" entity
Expected: Simpler schema, fewer queries
```

---

## Mock vs Production Mode

### Mock Mode (Current)
- Works without any database connections
- Uses realistic sample data
- Perfect for testing LLM recommendation logic
- **This is what you just ran!**

### Production Mode (When Ready)
Configure connections in `.env`:
```bash
NEO4J_URI=bolt://localhost:7687
TIMESCALEDB_URI=postgresql://localhost:5432/metrics
KAFKA_BROKERS=localhost:9092
```

System will:
- Read real query logs from Neo4j
- Store metrics in TimescaleDB
- Process events from Kafka
- Generate recommendations based on actual usage

---

## API Endpoints

### Health Check
```bash
curl http://localhost:8096/health
```

### Autonomous Ontology Health
```bash
curl http://localhost:8096/api/autonomous-ontology/health
```

### Generate Recommendations
```bash
curl -X POST http://localhost:8096/api/autonomous-ontology/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "YOUR_TENANT_ID",
    "domain": "real-estate",
    "time_window_days": 30,
    "min_priority": "medium"
  }'
```

Parameters:
- `tenant_id`: Your tenant identifier
- `domain`: Optional domain filter (e.g., "real-estate", "healthcare")
- `time_window_days`: How far back to analyze (default: 30)
- `min_priority`: Filter by priority ("low", "medium", "high", "critical")

---

## What's Next?

### Immediate (Phase 1-2 - ✅ Done)
- ✅ Collect usage metrics
- ✅ Generate AI recommendations

### Coming Soon (Phase 3-6)
- 🔄 **Phase 3:** Impact simulation (test changes in sandbox)
- 🔄 **Phase 4:** Human approval workflow (Slack/email notifications)
- 🔄 **Phase 5:** Automated execution (update YAML, generate code, deploy)
- 🔄 **Phase 6:** Monitoring & feedback (learn from outcomes)

### Try It Yourself

1. **Modify the mock data** in `collectors/usage_collector.py` to match your domain
2. **Experiment with prompts** in `recommendation/recommendation_engine.py`
3. **Try different LLM providers** (OpenAI, Anthropic, Ollama)
4. **Adjust priority thresholds** to filter recommendations

---

## Troubleshooting

### "LLM provider not configured"
- Check `.env` has `LLM_PROVIDER` and API key set
- Verify API key is valid

### "Module not found"
- Install dependencies: `pip install langchain langchain-openai`

### "Service won't start"
- Check port 8096 is available
- Check logs for error messages

### "No recommendations returned"
- Mock data should always return recommendations
- Check LLM API is accessible
- Check logs for LLM errors

---

## Cost Considerations

**LLM API Costs:**
- Each recommendation generation = 1 LLM call
- GPT-4 Turbo: ~$0.01-0.05 per request
- Claude 3 Sonnet: ~$0.003-0.015 per request
- Ollama (local): Free

**Recommendation:**
- Start with GPT-4 Turbo for best quality
- Move to Ollama for cost-free experimentation
- Cache recommendations to avoid redundant calls

---

## Architecture Diagram

```
User Request
    ↓
FastAPI Endpoint
    ↓
AutonomousOntologyOrchestrator
    ↓
┌─────────────────────────┬─────────────────────────┐
│  Phase 1: Collect       │  Phase 2: Recommend     │
│                         │                         │
│  UsageAnalyticsCollector│  RecommendationEngine   │
│  QueryLogCollector      │  (LLM: GPT-4/Claude)    │
│  MetricsAggregator      │                         │
│                         │                         │
│  Mock Data (for now)    │  Real AI Analysis       │
└─────────────────────────┴─────────────────────────┘
    ↓
Recommendations JSON
```

---

## Learn More

- **Full Documentation:** [AUTONOMOUS_ONTOLOGY_IMPLEMENTATION.md](./AUTONOMOUS_ONTOLOGY_IMPLEMENTATION.md)
- **Design Document:** [../../docs/architecture/AUTONOMOUS_ONTOLOGY_REFACTORING.md](../../docs/architecture/AUTONOMOUS_ONTOLOGY_REFACTORING.md)
- **AIP Architecture:** [../../docs/architecture/AIP_ARCHITECTURE_DESIGN.md](../../docs/architecture/AIP_ARCHITECTURE_DESIGN.md)

---

## Support

Questions? Issues?
1. Check the full implementation guide
2. Review the design document
3. Check service logs for errors
4. Open an issue in the repository

---

**Happy Ontology Refactoring! 🚀**
