# Agent System Refactoring: Hardcoded to YAML-Driven

**Status:** 🔴 Design Phase
**Priority:** High
**Timeline:** 6-8 weeks
**Repository:** binelek-ai

---

## Executive Summary

The current AI agent system in `binah-aip` has **4 hardcoded Python agents** specific to real estate. To support **20 domains**, we need to refactor to a **YAML-driven, domain-agnostic architecture**.

**Current State:**
- ❌ 4 hardcoded Python classes (1,287 lines of real estate-specific code)
- ❌ Single domain router (`/api/property/*`)
- ❌ Cannot deploy to healthcare, finance, logistics, etc.
- ❌ No agent configuration files

**Target State:**
- ✅ YAML-driven agent definitions in `domains/{domain}/agents.yaml`
- ✅ Generic `DomainAgent` base class that loads configuration
- ✅ `AgentRegistry` service that discovers all agents
- ✅ Dynamic routing: `/api/agents/{domain}/{agent_id}/execute`
- ✅ Tool system for entity queries, ML models, external APIs

---

## Current Architecture Analysis

### Hardcoded Agents Location

**Path:** `/services/binah-aip/app/agents/`

| Agent | File | Lines | Purpose |
|-------|------|-------|---------|
| PropertyAnalysisAgent | property_agent.py | 182 | Valuation, risk, ROI, market comparison |
| MarketResearchAgent | market_research_agent.py | 261 | Market trends, demographics, forecasts |
| DueDiligenceAgent | due_diligence_agent.py | 395 | Property inspection, legal review |
| PortfolioOptimizationAgent | portfolio_optimization_agent.py | 449 | Portfolio analysis, rebalancing |

### Current Agent Structure

```python
# app/agents/property_agent.py
class PropertyAnalysisAgent:
    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever

        # HARDCODED: Real estate-specific prompt
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a real estate analysis expert...

            1. **valuation**: Estimate property value based on:
               - Location and neighborhood
               - Property characteristics (size, age, condition)
               ...
            """),
            ("user", "Analyze this property: {property_id}...")
        ])

    async def analyze(self, request: PropertyAnalysisRequest):
        # HARDCODED: Real estate-specific data fetching
        property_data = await self._get_property_data(...)
        market_data = await self._get_market_data(...)

        # HARDCODED: Real estate-specific processing
        prompt = self.analysis_prompt.format_messages(...)
        response = await self.llm.ainvoke(prompt)
        return PropertyAnalysisResponse(...)
```

### Current Routing

```python
# app/routers/property.py
@router.post("/api/property/analyze")
async def analyze_property(request: PropertyAnalysisRequest):
    # HARDCODED: Direct import of specific agent
    from app.agents.property_agent import PropertyAnalysisAgent
    agent = PropertyAnalysisAgent(llm, retriever)
    response = await agent.analyze(request)
    return response
```

**Problem:** To support healthcare, we'd need:
- `HealthcareAgent`, `PatientRiskAgent`, `CareCoordinationAgent`, etc. (4 new agents)
- New router file: `app/routers/healthcare.py`
- Repeat for all 20 domains = **80 new Python files**

---

## Target Architecture

### YAML-Driven Agent Definitions

Each domain will have an `agents.yaml` file defining its agents:

**File:** `domains/real-estate/agents.yaml`

```yaml
agents:
  - id: property_analysis
    name: "Property Analysis Agent"
    version: "1.0.0"
    description: "Analyzes properties for valuation, risk assessment, and ROI calculations"

    # What this agent can do
    capabilities:
      - valuation
      - risk_assessment
      - roi_calculation
      - market_comparison

    # Tools available to this agent
    tools:
      - type: entity_query
        description: "Query property and market data from knowledge graph"
        entities:
          - Property
          - Transaction
          - Market
        queries:
          - property_by_id
          - market_trends
          - comparable_sales

      - type: ml_model
        description: "ML models for property valuation and risk scoring"
        models:
          - property_value_estimator
          - risk_scorer
          - market_trend_forecaster

      - type: external_api
        description: "External data sources"
        apis:
          - zillow_api
          - mls_feed

    # LLM prompt configuration
    prompt:
      system: |
        You are a real estate analysis expert with access to comprehensive property data.

        Your task is to analyze properties based on the request type:

        1. **valuation**: Estimate property value based on:
           - Location and neighborhood
           - Property characteristics (size, age, condition)
           - Comparable sales
           - Market trends

        2. **risk**: Assess investment risks:
           - Market volatility
           - Location risk factors
           - Property condition issues
           - Regulatory/zoning risks

        Provide:
        - Clear numerical estimates where possible
        - Confidence level (0-1)
        - Reasoning for your analysis
        - Actionable recommendations

      user: |
        Analyze this property:

        Property ID: {property_id}
        Analysis Type: {analysis_type}
        Property Data: {property_data}
        Market Data: {market_data}
        Parameters: {parameters}

        Provide your analysis as JSON:
        {
          "result": {
            "estimated_value": <number>,
            "key_metrics": {...},
            "risk_factors": [...]
          },
          "confidence": <0-1>,
          "reasoning": "<explanation>",
          "recommendations": ["rec1", "rec2"]
        }

    # Input/output schemas
    input_schema:
      type: object
      required: [property_id, analysis_type]
      properties:
        property_id:
          type: string
          format: uuid
        analysis_type:
          type: string
          enum: [valuation, risk, roi, market_comparison]
        parameters:
          type: object

    output_schema:
      type: object
      properties:
        result:
          type: object
        confidence:
          type: number
          minimum: 0
          maximum: 1
        reasoning:
          type: string
        recommendations:
          type: array
          items:
            type: string

  - id: market_research
    name: "Market Research Agent"
    version: "1.0.0"
    description: "Analyzes market trends, demographics, and forecasts"
    capabilities:
      - market_trends
      - demographic_analysis
      - price_forecasting
    tools:
      - type: entity_query
        entities: [Market, Demographics, Transaction]
      - type: ml_model
        models: [price_forecaster, trend_analyzer]
    prompt:
      system: "You are a market research analyst..."
      user: "Analyze market: {market_id}..."
    # ... (similar structure)
```

**Example for Healthcare:**

**File:** `domains/healthcare/agents.yaml`

```yaml
agents:
  - id: patient_risk_assessment
    name: "Patient Risk Assessment Agent"
    version: "1.0.0"
    description: "Assesses patient readmission risk and health deterioration"

    capabilities:
      - readmission_risk
      - complications_prediction
      - care_plan_recommendations

    tools:
      - type: entity_query
        entities:
          - Patient
          - Encounter
          - Diagnosis
          - Medication
        queries:
          - patient_history
          - recent_encounters
          - chronic_conditions

      - type: ml_model
        models:
          - readmission_predictor_v1
          - complications_risk_model
          - length_of_stay_estimator

      - type: external_api
        apis:
          - ehr_integration
          - pharmacy_data

    prompt:
      system: |
        You are a clinical analyst specializing in patient risk assessment.
        You have HIPAA-compliant access to patient data.

        Your task is to assess:
        1. **readmission_risk**: Predict 30-day readmission probability
        2. **complications_prediction**: Identify potential complications
        3. **care_plan_recommendations**: Suggest interventions

        Always:
        - Consider comorbidities and medication interactions
        - Account for social determinants of health
        - Provide evidence-based recommendations
        - Include confidence scores

      user: |
        Assess risk for patient:

        Patient ID: {patient_id}
        Assessment Type: {assessment_type}
        Recent History: {patient_history}
        Current Conditions: {conditions}

        Provide assessment as JSON...
```

---

## Implementation Plan

### Phase 1: Design & Schema (Week 1-2)

**Goal:** Define agent YAML schema and validate with existing agents

#### Task 1.1: Create Agent YAML Schema

**File:** `domains/_schema/agent.schema.yaml`

Define JSON Schema for agent definitions:
- Agent metadata (id, name, version, description)
- Capabilities list
- Tools configuration (entity_query, ml_model, external_api, actions)
- Prompt templates (system, user)
- Input/output schemas
- Security/permissions

**Deliverable:** Schema document validated with JSON Schema validator

#### Task 1.2: Convert 4 Existing Agents to YAML

Create `domains/real-estate/agents.yaml` with:
1. PropertyAnalysisAgent → `property_analysis`
2. MarketResearchAgent → `market_research`
3. DueDiligenceAgent → `due_diligence`
4. PortfolioOptimizationAgent → `portfolio_optimization`

**Validation:** Compare YAML definition to Python implementation line-by-line

#### Task 1.3: Design Tool Specification

Define how tools are specified and executed:

```yaml
tools:
  - type: entity_query
    name: "Get property details"
    action: neo4j_query
    query: |
      MATCH (p:Property {id: $property_id})
      OPTIONAL MATCH (p)-[:LOCATED_IN]->(loc:Location)
      RETURN p, loc
    parameters:
      - property_id
    output: object

  - type: ml_model
    name: "Property value estimator"
    model_id: "property_value_estimator_v2"
    endpoint: "http://binah-ml:8109/api/ml/predict"
    input_mapping:
      size_sqft: "{entity.size_sqft}"
      bedrooms: "{entity.bedrooms}"
      location: "{entity.location}"
    output_mapping:
      estimated_value: "prediction.value"
      confidence: "prediction.confidence"
```

---

### Phase 2: Runtime Infrastructure (Week 3-5)

**Goal:** Build generic agent execution engine

#### Task 2.1: Create `DomainAgent` Base Class

**File:** `app/agents/base_agent.py`

```python
class DomainAgent:
    """
    Generic agent that loads configuration from YAML and executes tasks.

    Replaces all hardcoded agent classes.
    """

    def __init__(
        self,
        agent_config: dict,
        llm: BaseLLM,
        tool_executor: ToolExecutor,
        tenant_context: TenantContext
    ):
        self.config = agent_config
        self.llm = llm
        self.tool_executor = tool_executor
        self.tenant_context = tenant_context

        # Load prompt template from config
        self.prompt_template = self._load_prompt_template()

    async def execute(self, request: AgentExecutionRequest) -> AgentExecutionResponse:
        """
        Execute agent task based on YAML configuration

        Steps:
        1. Validate input against input_schema
        2. Execute tools to gather data
        3. Format prompt with data
        4. Invoke LLM
        5. Parse response
        6. Validate output against output_schema
        """
        # Validate input
        self._validate_input(request.input_data)

        # Execute tools
        tool_results = await self._execute_tools(request)

        # Format prompt
        prompt_data = {
            **request.input_data,
            **tool_results
        }
        prompt = self.prompt_template.format(**prompt_data)

        # Invoke LLM
        response = await self.llm.ainvoke(prompt)

        # Parse and validate output
        output = self._parse_response(response)
        self._validate_output(output)

        return AgentExecutionResponse(
            agent_id=self.config["id"],
            output=output,
            metadata={
                "tools_executed": list(tool_results.keys()),
                "tokens_used": response.tokens,
                "duration_ms": ...
            }
        )

    async def _execute_tools(self, request: AgentExecutionRequest) -> dict:
        """Execute all tools defined in agent config"""
        results = {}
        for tool_config in self.config.get("tools", []):
            tool_result = await self.tool_executor.execute(
                tool_config=tool_config,
                input_data=request.input_data,
                tenant_id=self.tenant_context.tenant_id
            )
            results[tool_config["name"]] = tool_result
        return results
```

**Tests:** Unit tests for DomainAgent with mock configs

#### Task 2.2: Create `ToolExecutor` Service

**File:** `app/agents/tool_executor.py`

```python
class ToolExecutor:
    """
    Executes tools defined in agent YAML configurations.

    Supported tool types:
    - entity_query: Neo4j queries
    - ml_model: Calls to binah-ml
    - external_api: HTTP requests to external services
    - actions: Write operations (create entity, update, etc.)
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        ml_client: MLServiceClient,
        http_client: HTTPClient,
        tenant_context: TenantContext
    ):
        self.neo4j = neo4j_client
        self.ml = ml_client
        self.http = http_client
        self.tenant_context = tenant_context

    async def execute(
        self,
        tool_config: dict,
        input_data: dict,
        tenant_id: str
    ) -> Any:
        """Execute a tool based on its type"""
        tool_type = tool_config["type"]

        if tool_type == "entity_query":
            return await self._execute_entity_query(tool_config, input_data, tenant_id)
        elif tool_type == "ml_model":
            return await self._execute_ml_model(tool_config, input_data, tenant_id)
        elif tool_type == "external_api":
            return await self._execute_external_api(tool_config, input_data, tenant_id)
        elif tool_type == "actions":
            return await self._execute_action(tool_config, input_data, tenant_id)
        else:
            raise ValueError(f"Unknown tool type: {tool_type}")

    async def _execute_entity_query(
        self,
        tool_config: dict,
        input_data: dict,
        tenant_id: str
    ) -> dict:
        """Execute Neo4j query with tenant isolation"""
        query = tool_config["query"]
        parameters = {k: input_data.get(k) for k in tool_config.get("parameters", [])}
        parameters["tenant_id"] = tenant_id  # CRITICAL: Tenant isolation

        result = await self.neo4j.run_query(query, parameters)
        return self._map_output(result, tool_config.get("output_mapping", {}))

    async def _execute_ml_model(
        self,
        tool_config: dict,
        input_data: dict,
        tenant_id: str
    ) -> dict:
        """Call ML model via binah-ml service"""
        model_id = tool_config["model_id"]
        endpoint = tool_config.get("endpoint", f"http://binah-ml:8109/api/ml/predict/{model_id}")

        # Map input data to model format
        model_input = self._map_input(input_data, tool_config.get("input_mapping", {}))

        # Call ML service
        response = await self.ml.predict(
            model_id=model_id,
            input_data=model_input,
            tenant_id=tenant_id
        )

        # Map output back
        return self._map_output(response, tool_config.get("output_mapping", {}))
```

**Tests:** Integration tests with mock Neo4j and ML service

#### Task 2.3: Create `AgentRegistry` Service

**File:** `app/services/agent_registry.py`

```python
class AgentRegistry:
    """
    Loads and manages all agent definitions from domain YAML files.

    Discovers agents from:
    - domains/{domain}/agents.yaml (from domain-registry service)
    - Local file system (development)
    """

    def __init__(self, domain_registry_client: DomainRegistryClient):
        self.domain_registry = domain_registry_client
        self._agents: Dict[str, Dict[str, dict]] = {}  # {domain: {agent_id: config}}

    async def load_agents(self):
        """Load all agent definitions from all domains"""
        domains = await self.domain_registry.get_all_domains()

        for domain in domains:
            domain_id = domain["id"]
            agents_config = await self.domain_registry.get_agents(domain_id)

            if agents_config:
                self._agents[domain_id] = {
                    agent["id"]: agent
                    for agent in agents_config.get("agents", [])
                }

    def get_agent_config(self, domain: str, agent_id: str) -> Optional[dict]:
        """Get agent configuration"""
        return self._agents.get(domain, {}).get(agent_id)

    def list_agents(self, domain: Optional[str] = None) -> List[dict]:
        """List all agents (optionally filtered by domain)"""
        if domain:
            return list(self._agents.get(domain, {}).values())

        all_agents = []
        for domain_agents in self._agents.values():
            all_agents.extend(domain_agents.values())
        return all_agents
```

**Tests:** Unit tests with mock domain-registry responses

#### Task 2.4: Add Agent Endpoints to Domain Registry

**File:** `binah-domain-registry` (separate repo: binelek-codegen)

Add new endpoint to serve agent configurations:

```csharp
[HttpGet("api/domains/{domainId}/agents")]
public async Task<IActionResult> GetAgents(string domainId)
{
    var agentsPath = Path.Combine(_domainsDirectory, domainId, "agents.yaml");

    if (!System.IO.File.Exists(agentsPath))
    {
        return NotFound(new { error = $"No agents defined for domain: {domainId}" });
    }

    var yaml = await System.IO.File.ReadAllTextAsync(agentsPath);
    var agents = _yamlParser.Parse<AgentsConfiguration>(yaml);

    return Ok(agents);
}
```

#### Task 2.5: Create Dynamic Agent Router

**File:** `app/routers/agents.py` (NEW)

```python
router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/{domain}/{agent_id}/execute")
async def execute_agent(
    domain: str,
    agent_id: str,
    request: AgentExecutionRequest,
    current_user: TokenData = Depends(get_current_user),
    agent_registry: AgentRegistry = Depends(get_agent_registry),
    tool_executor: ToolExecutor = Depends(get_tool_executor),
    llm: BaseLLM = Depends(get_llm)
):
    """
    Execute any agent from any domain - GENERIC ENDPOINT

    Examples:
    - POST /api/agents/real-estate/property_analysis/execute
    - POST /api/agents/healthcare/patient_risk_assessment/execute
    - POST /api/agents/finance/portfolio_optimization/execute
    """
    # Validate tenant isolation
    validate_tenant_isolation(current_user.tenant_id, request.tenant_id)

    # Get agent configuration
    agent_config = agent_registry.get_agent_config(domain, agent_id)
    if not agent_config:
        raise HTTPException(404, f"Agent not found: {domain}/{agent_id}")

    # Create agent instance
    agent = DomainAgent(
        agent_config=agent_config,
        llm=llm,
        tool_executor=tool_executor,
        tenant_context=TenantContext(tenant_id=current_user.tenant_id)
    )

    # Execute
    response = await agent.execute(request)
    return response
```

**Deprecate:** Mark `/api/property/*` routes as deprecated

---

### Phase 3: Migration & Testing (Week 6-7)

**Goal:** Migrate existing agents and create new domain agents

#### Task 3.1: Convert Existing Agents to YAML

1. Real Estate (4 agents) - Already done in Phase 1
2. Test with existing integration tests
3. Verify feature parity with hardcoded versions

#### Task 3.2: Create Healthcare Agents

**File:** `domains/healthcare/agents.yaml`

Create 4 healthcare agents:
1. `patient_risk_assessment` - Readmission risk, complications
2. `care_coordination` - Care plan optimization
3. `clinical_documentation` - Generate clinical notes
4. `diagnosis_assistant` - Differential diagnosis support

**Test:** Create sample healthcare tenant and test all 4 agents

#### Task 3.3: Create Finance Agents

**File:** `domains/finance/agents.yaml`

Create 4 finance agents:
1. `portfolio_analysis` - Portfolio performance and risk
2. `investment_recommendations` - Stock/fund recommendations
3. `risk_assessment` - Market risk and compliance
4. `compliance_monitoring` - Regulatory compliance checks

#### Task 3.4: Integration Testing

Test matrix:
- [ ] Real estate agents work with YAML
- [ ] Healthcare agents execute correctly
- [ ] Finance agents execute correctly
- [ ] Cross-domain agent execution
- [ ] Tenant isolation maintained
- [ ] Performance benchmarks (< 2s response time)
- [ ] Error handling (invalid YAML, missing tools, etc.)

---

### Phase 4: Documentation & Rollout (Week 8)

**Goal:** Document agent system and roll out to production

#### Task 4.1: Developer Documentation

Create documentation:
1. **Agent Creation Guide** - How to define new agents
2. **Tool System Reference** - Available tools and their configuration
3. **API Reference** - New `/api/agents/*` endpoints
4. **Migration Guide** - How to convert hardcoded agents to YAML
5. **Best Practices** - Prompt engineering, tool selection, testing

#### Task 4.2: Update Platform Documentation

Update `binelek-docs`:
- [ ] Update AI Platform overview with new agent system
- [ ] Add agent creation tutorials for each domain
- [ ] Update architecture diagrams
- [ ] Create video walkthrough of agent creation

#### Task 4.3: Production Rollout

1. Deploy to staging environment
2. Run full test suite
3. Performance testing (load test with 1000 concurrent agent executions)
4. Deploy to production with feature flag
5. Gradual rollout: 10% → 50% → 100% traffic
6. Monitor metrics (response time, error rate, agent execution count)

#### Task 4.4: Deprecation Plan

1. Week 1-4: Mark old endpoints as deprecated (still functional)
2. Week 5-8: Add warnings to API responses
3. Week 9-12: Notify all API consumers
4. Week 13+: Remove old hardcoded agents

---

## Technical Specifications

### Agent YAML Schema (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["agents"],
  "properties": {
    "agents": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "version", "capabilities", "prompt"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^[a-z0-9_]+$",
            "description": "Unique agent identifier (lowercase, underscores)"
          },
          "name": {
            "type": "string",
            "description": "Human-readable agent name"
          },
          "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "description": "Semantic version (e.g., 1.0.0)"
          },
          "description": {
            "type": "string"
          },
          "capabilities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of capabilities this agent provides"
          },
          "tools": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["type"],
              "properties": {
                "type": {
                  "enum": ["entity_query", "ml_model", "external_api", "actions"]
                }
              }
            }
          },
          "prompt": {
            "type": "object",
            "required": ["system", "user"],
            "properties": {
              "system": {"type": "string"},
              "user": {"type": "string"}
            }
          },
          "input_schema": {
            "type": "object",
            "description": "JSON Schema for input validation"
          },
          "output_schema": {
            "type": "object",
            "description": "JSON Schema for output validation"
          }
        }
      }
    }
  }
}
```

### API Specification

**New Endpoint:**

```
POST /api/agents/{domain}/{agent_id}/execute
```

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "input_data": {
    "property_id": "550e8400-e29b-41d4-a716-446655440000",
    "analysis_type": "valuation",
    "parameters": {
      "include_market_trends": true
    }
  }
}
```

**Response:**
```json
{
  "agent_id": "property_analysis",
  "domain": "real-estate",
  "output": {
    "result": {
      "estimated_value": 450000,
      "key_metrics": {
        "price_per_sqft": 180,
        "cap_rate": 0.065
      },
      "risk_factors": ["Market volatility", "Property age"]
    },
    "confidence": 0.85,
    "reasoning": "Based on comparable sales...",
    "recommendations": [
      "Consider recent neighborhood developments",
      "Review property condition assessment"
    ]
  },
  "metadata": {
    "tools_executed": ["entity_query", "ml_model"],
    "tokens_used": 1250,
    "duration_ms": 1450,
    "timestamp": "2025-01-20T10:30:00Z"
  }
}
```

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| YAML parsing errors | Medium | Medium | Comprehensive validation, clear error messages |
| Performance degradation | Low | High | Benchmark testing, caching agent configs |
| Tool execution failures | Medium | High | Robust error handling, retry logic, fallbacks |
| LLM prompt injection | Medium | High | Input sanitization, prompt templates with escaping |
| Breaking existing API consumers | High | High | Feature flags, gradual rollout, deprecation period |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Agent config errors in production | Low | High | Config validation in CI/CD, staging environment |
| Missing agent definitions | Low | Medium | Default fallback agents, clear error messages |
| Tenant data leakage | Low | Critical | Mandatory tenant_id in all tool executions, auditing |

---

## Success Metrics

### Performance Metrics

- Agent execution time: < 2s (p95)
- Tool execution time: < 500ms per tool (p95)
- Config loading time: < 100ms (p95)
- Concurrent executions: > 1000/sec

### Adoption Metrics

- Number of domains with agents: 20 (target)
- Number of custom agents created: 50+ (6 months post-launch)
- API call migration: 100% of old endpoints migrated within 3 months
- Agent marketplace submissions: 10+ (12 months post-launch)

### Quality Metrics

- Agent execution success rate: > 99%
- YAML validation pass rate: > 95%
- Test coverage: > 90%
- Documentation completeness: 100%

---

## Next Steps

1. **Review & Approve This Plan** - Engineering leadership review
2. **Create GitHub Issues** - Break down into implementable tasks
3. **Assign Phase 1 Tasks** - Start with agent YAML schema design
4. **Set Up Project Board** - Track progress across 8 weeks
5. **Schedule Kickoff Meeting** - Align team on vision and timeline

---

## References

- **Agent Creation Framework:** `/developer-site/docs/internal/architecture/AGENT_CREATION_FRAMEWORK.md` (binelek-docs)
- **Current Agent Code:** `/services/binah-aip/app/agents/` (this repo)
- **Domain Definitions:** `/domains/` (this repo)
- **LLM Provider Implementation:** `LLM_PROVIDER_IMPLEMENTATION_REPORT.md` (this repo)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-21
**Author:** Technical Architecture Team
**Status:** 🔴 Awaiting Approval
