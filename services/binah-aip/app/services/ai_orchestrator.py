"""AI Orchestrator - Central coordination for AI query processing"""

from app.services.query_router import QueryRouter
from app.services.task_planner import TaskPlanner
from app.services.hybrid_retriever import HybridRetriever
from app.models import QueryRequest, AIResponse, AuditLogEntry
from app.config import settings
from datetime import datetime
from uuid import uuid4
import logging
import time

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Central orchestrator for AI-powered query processing

    Coordinates query routing, task planning, tool execution,
    and response synthesis across multiple AI agents and data sources.
    """

    def __init__(self, llm, embedding_model=None):
        self.llm = llm
        self.embedding_model = embedding_model

        # Core components
        self.query_router = QueryRouter(llm)
        self.task_planner = TaskPlanner(llm)
        self.hybrid_retriever = HybridRetriever()

        # Specialized agents (to be initialized)
        self.agents = {}

        # Audit log storage
        self.audit_logs = []

    async def process_query(
        self,
        request: QueryRequest
    ) -> AIResponse:
        """
        Process a natural language query end-to-end

        Args:
            request: QueryRequest with query, tenant_id, and context

        Returns:
            AIResponse with answer and reasoning
        """
        start_time = time.time()
        query_id = uuid4()

        logger.info(f"Processing query {query_id} for tenant {request.tenant_id}: {request.query}")

        try:
            # Step 1: Route query to determine type
            query_type = await self.query_router.classify(request.query)
            logger.info(f"Query classified as: {query_type.type} (confidence: {query_type.confidence})")

            # Step 2: Create execution plan
            plan = await self.task_planner.plan(
                query=request.query,
                query_type=query_type,
                tenant_id=str(request.tenant_id),
                context=request.context
            )
            logger.info(f"Created plan with {len(plan.steps)} steps")

            # Step 3: Execute plan steps
            execution_results = await self._execute_plan(
                plan=plan,
                tenant_id=str(request.tenant_id),
                context=request.context or {}
            )

            # Step 4: Retrieve relevant context via hybrid retrieval
            if query_type.type in ["factual", "analytical"]:
                retrieved_context = await self.hybrid_retriever.retrieve(
                    query=request.query,
                    tenant_id=str(request.tenant_id),
                    retrieval_type="hybrid",
                    limit=10
                )
                execution_results["retrieved_context"] = retrieved_context

            # Step 5: Synthesize final response
            answer = await self._synthesize_response(
                query=request.query,
                query_type=query_type,
                execution_results=execution_results,
                context=request.context or {}
            )

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Create response
            response = AIResponse(
                query_id=query_id,
                tenant_id=request.tenant_id,
                query=request.query,
                query_type=query_type.type,
                answer=answer,
                confidence=query_type.confidence,
                reasoning_steps=[
                    {"step": "classification", "result": query_type.dict()},
                    {"step": "planning", "result": plan.dict()},
                    {"step": "execution", "result": execution_results}
                ],
                sources=execution_results.get("retrieved_context", [])[:5],
                metadata={
                    "tools_used": plan.tools_required,
                    "complexity": plan.estimated_complexity
                },
                processing_time_ms=processing_time_ms
            )

            # Step 6: Audit log
            await self._log_interaction(request, response, plan.tools_required, processing_time_ms)

            logger.info(f"Query {query_id} processed in {processing_time_ms}ms")
            return response

        except Exception as e:
            logger.error(f"Error processing query {query_id}: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)

            return AIResponse(
                query_id=query_id,
                tenant_id=request.tenant_id,
                query=request.query,
                query_type="error",
                answer=f"I encountered an error processing your query: {str(e)}",
                confidence=0.0,
                processing_time_ms=processing_time_ms
            )

    async def _execute_plan(
        self,
        plan,
        tenant_id: str,
        context: dict
    ) -> dict:
        """Execute the planned steps"""
        results = {
            "steps_executed": [],
            "data_gathered": []
        }

        for step in plan.steps:
            tool = step.get("tool")
            action = step.get("action")
            parameters = step.get("parameters", {})

            logger.info(f"Executing step: {action} using {tool}")

            # Route to appropriate tool
            if tool == "neo4j_query":
                step_result = await self._execute_graph_query(tenant_id, parameters)
            elif tool == "vector_search":
                step_result = await self._execute_vector_search(tenant_id, parameters)
            elif tool == "ml_predict":
                step_result = await self._execute_ml_prediction(parameters)
            elif tool == "property_agent":
                step_result = await self._execute_property_agent(tenant_id, parameters)
            else:
                step_result = {"status": "not_implemented", "tool": tool}

            results["steps_executed"].append({
                "tool": tool,
                "action": action,
                "result": step_result
            })

            if step_result.get("data"):
                results["data_gathered"].extend(step_result["data"])

        return results

    async def _execute_graph_query(self, tenant_id: str, parameters: dict) -> dict:
        """Execute Neo4j graph query"""
        try:
            # Placeholder - would actually query Neo4j
            return {
                "status": "success",
                "data": [{"message": "Graph query executed (placeholder)"}]
            }
        except Exception as e:
            logger.error(f"Graph query error: {e}")
            return {"status": "error", "error": str(e)}

    async def _execute_vector_search(self, tenant_id: str, parameters: dict) -> dict:
        """Execute vector search in Qdrant"""
        try:
            query = parameters.get("query", "")
            results = await self.hybrid_retriever.retrieve(
                query=query,
                tenant_id=tenant_id,
                retrieval_type="vector",
                limit=parameters.get("limit", 10)
            )
            return {"status": "success", "data": results}
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return {"status": "error", "error": str(e)}

    async def _execute_ml_prediction(self, parameters: dict) -> dict:
        """Execute ML model prediction"""
        # Placeholder for ML model execution
        return {
            "status": "success",
            "data": [{"message": "ML prediction executed (placeholder)"}]
        }

    async def _execute_property_agent(self, tenant_id: str, parameters: dict) -> dict:
        """Execute property analysis agent"""
        # Placeholder for property agent
        return {
            "status": "success",
            "data": [{"message": "Property agent executed (placeholder)"}]
        }

    async def _synthesize_response(
        self,
        query: str,
        query_type,
        execution_results: dict,
        context: dict
    ) -> str:
        """Synthesize final response from execution results"""
        from langchain.prompts import ChatPromptTemplate

        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant for a real estate knowledge graph platform.

Synthesize a clear, accurate response to the user's query based on the execution results.

Guidelines:
- Be concise and direct
- Cite specific data points when available
- If data is unavailable, acknowledge it
- For analytical queries, provide insights
- For predictive queries, explain confidence levels"""),
            ("user", """Query: {query}
Query Type: {query_type}

Execution Results:
{results}

Provide a helpful response to the user.""")
        ])

        try:
            prompt = synthesis_prompt.format_messages(
                query=query,
                query_type=query_type.type,
                results=str(execution_results)[:2000]  # Limit context size
            )

            response = await self.llm.ainvoke(prompt)
            return response.content

        except Exception as e:
            logger.error(f"Response synthesis error: {e}")
            return "I was able to process your query, but encountered an error generating a response. Please try again."

    async def _log_interaction(
        self,
        request: QueryRequest,
        response: AIResponse,
        tools_used: list[str],
        processing_time_ms: int
    ):
        """Log AI interaction for audit trail"""
        log_entry = AuditLogEntry(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            query=request.query,
            query_type=response.query_type,
            response_summary=response.answer[:200],
            tools_used=tools_used,
            processing_time_ms=processing_time_ms
        )

        self.audit_logs.append(log_entry)

        # In production, would write to database
        logger.info(f"Logged interaction: {log_entry.id}")

    async def close(self):
        """Clean up resources"""
        await self.hybrid_retriever.close()
