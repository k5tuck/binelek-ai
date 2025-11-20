"""
AI Recommendation Engine

Uses LLMs to analyze usage patterns and generate ontology improvement recommendations.
This is the core of Phase 2 - the "brain" of the autonomous ontology system.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from ..models import (
    UsageMetrics,
    Recommendation,
    RecommendationType,
    Priority,
    Implementation,
    YAMLChange,
    MigrationStrategy
)

logger = logging.getLogger(__name__)


class RecommendationOutput(BaseModel):
    """Structured output format for LLM recommendations"""
    recommendations: List[Dict[str, Any]] = Field(
        description="List of ontology improvement recommendations"
    )


class RecommendationEngine:
    """
    AI-powered recommendation generation engine.

    Uses LLM (GPT-4/Claude) to analyze usage patterns and generate
    actionable ontology improvement suggestions.

    Implements the approach outlined in AUTONOMOUS_ONTOLOGY_REFACTORING.md
    """

    def __init__(self, llm):
        """
        Initialize the recommendation engine.

        Args:
            llm: LangChain LLM instance (OpenAI, Anthropic, or Ollama)
        """
        self.llm = llm
        self.output_parser = PydanticOutputParser(pydantic_object=RecommendationOutput)
        logger.info("RecommendationEngine initialized")

    async def generate_recommendations(
        self,
        metrics: UsageMetrics,
        aggregations: Dict[str, Any],
        domain: Optional[str] = None,
        min_priority: Priority = Priority.LOW
    ) -> List[Recommendation]:
        """
        Generate ontology improvement recommendations based on usage patterns.

        Args:
            metrics: Raw usage metrics
            aggregations: Aggregated insights
            domain: Optional domain filter
            min_priority: Minimum priority level

        Returns:
            List of Recommendation objects
        """
        logger.info(
            f"Generating recommendations for tenant={metrics.tenant_id}, "
            f"domain={domain}"
        )

        # Build comprehensive analysis prompt
        prompt = self._build_analysis_prompt(metrics, aggregations, domain)

        # Get LLM recommendations
        try:
            response = await self.llm.ainvoke(prompt)
            raw_recommendations = self._parse_llm_response(response.content)

            # Convert to Recommendation objects
            recommendations = []
            for idx, rec_data in enumerate(raw_recommendations):
                try:
                    rec = self._create_recommendation(
                        rec_data,
                        metrics.tenant_id,
                        domain or "general",
                        idx
                    )

                    # Filter by priority
                    if self._priority_value(rec.priority) >= self._priority_value(min_priority):
                        recommendations.append(rec)

                except Exception as e:
                    logger.error(f"Error creating recommendation: {e}")
                    continue

            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def _build_analysis_prompt(
        self,
        metrics: UsageMetrics,
        aggregations: Dict[str, Any],
        domain: Optional[str]
    ) -> str:
        """
        Build the comprehensive analysis prompt for the LLM.

        This is the critical prompt that guides the AI to make good recommendations.
        Based on the prompt template in AUTONOMOUS_ONTOLOGY_REFACTORING.md
        """

        summary = aggregations.get("summary", {})
        top_entities = aggregations.get("top_entities", [])
        slow_queries = aggregations.get("slow_queries", [])
        coaccessed_entities = aggregations.get("coaccessed_entities", [])
        data_quality_issues = aggregations.get("data_quality_issues", [])
        performance_issues = aggregations.get("performance_issues", [])

        prompt = f"""
You are an expert ontology architect analyzing usage patterns for a multi-domain knowledge graph platform.

**ONTOLOGY CONTEXT:**
- System: Binelek Platform (Multi-tenant Real Estate Knowledge Graph)
- Tenant ID: {metrics.tenant_id}
- Domain: {domain or "Multi-domain"}
- Time Window: {metrics.time_window_start.date()} to {metrics.time_window_end.date()}

**CURRENT ONTOLOGY SUMMARY:**
- Total Entities: {summary.get('total_entity_types', 0)}
- Total Relationships: {summary.get('total_relationship_types', 0)}
- Total Queries (30 days): {summary.get('total_queries', 0)}
- Queries per Day: {summary.get('queries_per_day', 0):.1f}

**TOP ACCESSED ENTITIES:**
{json.dumps(top_entities, indent=2)}

**PERFORMANCE ISSUES:**
{json.dumps(slow_queries[:5], indent=2)}

**CO-ACCESSED ENTITIES (Potential New Relationships):**
{json.dumps(coaccessed_entities, indent=2)}

**DATA QUALITY ISSUES:**
{json.dumps(data_quality_issues, indent=2)}

**PERFORMANCE BOTTLENECKS:**
{json.dumps(performance_issues[:5], indent=2)}

---

**YOUR TASK:**
Analyze the usage patterns above and suggest improvements in these categories:

1. **Entity Consolidation**
   - Identify entities that are frequently used together with >80% overlapping usage
   - Suggest merging similar entities to reduce complexity

2. **New Relationships**
   - Detect implicit relationships from query patterns
   - Example: If queries frequently traverse Property → Owner → Transaction,
     suggest a direct Property → Transaction relationship
   - Focus on relationships traversed >50 times

3. **Computed Fields**
   - Identify repeated calculations in queries
   - Suggest adding computed properties to entities
   - Example: If queries often calculate "age" from "date_of_birth", add an "age" computed field

4. **Index Optimization**
   - Find frequently-filtered properties without indexes
   - Suggest composite indexes for common query patterns
   - Focus on properties accessed >100 times

5. **Validation Rules**
   - Detect data quality issues (high null rates >30%, invalid formats)
   - Suggest validation rules to prevent future issues

6. **Entity Deprecation**
   - Identify rarely-used entities (<10 accesses in 30 days)
   - Suggest deprecation if truly unused

---

**OUTPUT FORMAT (JSON):**
Return a JSON object with a "recommendations" array. Each recommendation should have:

```json
{{
  "recommendations": [
    {{
      "type": "entity_consolidation | new_relationship | computed_field | index | validation | deprecate_entity",
      "priority": "low | medium | high | critical",
      "title": "Brief description (50 chars)",
      "rationale": "Why this improvement is suggested (2-3 sentences)",
      "impact": "Expected benefits (1-2 sentences)",
      "risk": "Potential breaking changes or risks (1-2 sentences)",
      "implementation": {{
        "yaml_changes_description": "High-level description of YAML changes needed",
        "migration_required": true/false,
        "estimated_effort_hours": 1.0,
        "breaking_changes": ["list", "of", "breaking", "changes"]
      }},
      "predicted_improvement": 15.5,
      "supporting_data": {{
        "affected_entities": ["Entity1", "Entity2"],
        "frequency": 150,
        "current_performance": "75ms avg",
        "expected_performance": "25ms avg"
      }}
    }}
  ]
}}
```

**IMPORTANT GUIDELINES:**
- Only suggest changes with clear data-driven rationale
- Prioritize high-impact, low-risk changes
- Be conservative with breaking changes
- Consider tenant-specific domain context
- Provide concrete, actionable recommendations
- Each recommendation should be independently implementable

Generate your recommendations now:
"""

        return prompt

    def _parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract recommendations.

        Handles both JSON and text responses gracefully.
        """
        try:
            # Try to parse as JSON
            if "```json" in response_text:
                # Extract JSON from markdown code block
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            elif "{" in response_text:
                # Find JSON object in response
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_text = response_text[start:end]
            else:
                logger.warning("No JSON found in LLM response")
                return []

            parsed = json.loads(json_text)
            recommendations = parsed.get("recommendations", [])

            logger.info(f"Parsed {len(recommendations)} recommendations from LLM")
            return recommendations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            return []

    def _create_recommendation(
        self,
        rec_data: Dict[str, Any],
        tenant_id: str,
        domain: str,
        index: int
    ) -> Recommendation:
        """Create a Recommendation object from LLM output"""

        # Generate unique ID
        rec_id = f"rec-{tenant_id}-{int(datetime.utcnow().timestamp())}-{index}"

        # Extract implementation details
        impl_data = rec_data.get("implementation", {})
        migration_required = impl_data.get("migration_required", False)

        implementation = Implementation(
            yaml_changes=[],  # Will be populated later
            migration_strategy=MigrationStrategy(
                required=migration_required,
                affected_records=0,  # Will be calculated in simulation
                estimated_duration="Unknown",
                backfill_strategy="lazy"
            ),
            estimated_effort_hours=impl_data.get("estimated_effort_hours", 1.0),
            breaking_changes=impl_data.get("breaking_changes", [])
        )

        # Create recommendation
        return Recommendation(
            id=rec_id,
            type=RecommendationType(rec_data.get("type", "new_relationship")),
            priority=Priority(rec_data.get("priority", "medium")),
            title=rec_data.get("title", "Untitled Recommendation"),
            rationale=rec_data.get("rationale", ""),
            impact=rec_data.get("impact", ""),
            risk=rec_data.get("risk", ""),
            tenant_id=tenant_id,
            domain=domain,
            implementation=implementation,
            usage_metrics=rec_data.get("supporting_data", {}),
            predicted_improvement=rec_data.get("predicted_improvement", 0.0)
        )

    def _priority_value(self, priority: Priority) -> int:
        """Convert priority to numeric value for comparison"""
        priority_map = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4
        }
        return priority_map.get(priority, 0)
