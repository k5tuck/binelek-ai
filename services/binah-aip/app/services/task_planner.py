"""Task Planner - Creates execution plans for complex queries"""

from langchain.prompts import ChatPromptTemplate
from app.models import ExecutionPlan, QueryType
from app.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class TaskPlanner:
    """Plans multi-step execution for complex queries"""

    def __init__(self, llm):
        self.llm = llm

        self.planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a task planning expert for a real estate AI platform.

Given a user query and its classification, create a step-by-step execution plan.

Available tools:
- neo4j_query: Query the knowledge graph (properties, contractors, investors, etc.)
- vector_search: Semantic search over documents and embeddings
- sql_query: Query structured pipeline data
- property_agent: Analyze specific properties
- market_agent: Research market trends
- ml_predict: Run ML predictions (cost, risk, ROI)

For each step, specify:
1. tool: Which tool to use
2. action: What to do
3. parameters: What inputs to provide

Respond with JSON:
{{
  "steps": [
    {{"step": 1, "tool": "neo4j_query", "action": "Find properties", "parameters": {{"filters": ...}}}},
    {{"step": 2, "tool": "ml_predict", "action": "Predict ROI", "parameters": {{"property_ids": ...}}}}
  ],
  "tools_required": ["neo4j_query", "ml_predict"],
  "estimated_complexity": "medium"
}}"""),
            ("user", """Query: {query}
Query Type: {query_type}
Tenant ID: {tenant_id}

Create an execution plan.""")
        ])

    async def plan(
        self,
        query: str,
        query_type: QueryType,
        tenant_id: str,
        context: dict | None = None
    ) -> ExecutionPlan:
        """
        Create an execution plan for the query

        Args:
            query: Natural language query
            query_type: Classification result
            tenant_id: Tenant ID for data isolation
            context: Additional context

        Returns:
            ExecutionPlan with steps to execute
        """
        try:
            prompt = self.planning_prompt.format_messages(
                query=query,
                query_type=query_type.type,
                tenant_id=tenant_id
            )

            response = await self.llm.ainvoke(prompt)

            # Parse JSON response
            plan_data = json.loads(response.content)

            plan = ExecutionPlan(**plan_data)

            logger.info(f"Created plan with {len(plan.steps)} steps, complexity: {plan.estimated_complexity}")
            return plan

        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            # Fallback to simple plan
            return ExecutionPlan(
                steps=[{"step": 1, "tool": "neo4j_query", "action": "Search knowledge graph", "parameters": {"query": query}}],
                tools_required=["neo4j_query"],
                estimated_complexity="low"
            )
