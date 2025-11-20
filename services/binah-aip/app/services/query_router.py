"""Query Router - Classifies incoming queries by type and intent"""

from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from app.models import QueryType
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class QueryRouter:
    """Routes queries to appropriate handlers based on classification"""

    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=QueryType)

        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query classification expert for a real estate knowledge graph platform.

Classify the user's query into one of these categories:

1. **factual**: Simple fact retrieval (e.g., "What properties are in Austin?", "Show me Project X details")
2. **analytical**: Analysis requiring aggregation or comparison (e.g., "Compare ROI across portfolios", "What are the trends?")
3. **predictive**: Future predictions using ML models (e.g., "Predict cost overruns", "Forecast property value")
4. **conversational**: Casual chat or clarification questions (e.g., "Hello", "Can you explain that?")

Respond with JSON containing:
- type: The category (factual, analytical, predictive, conversational)
- confidence: Float 0-1
- reasoning: Brief explanation

{format_instructions}"""),
            ("user", "{query}")
        ])

    async def classify(self, query: str) -> QueryType:
        """
        Classify the query type

        Args:
            query: Natural language query from user

        Returns:
            QueryType with classification result
        """
        try:
            prompt = self.classification_prompt.format_messages(
                query=query,
                format_instructions=self.parser.get_format_instructions()
            )

            response = await self.llm.ainvoke(prompt)

            # Parse the response
            result = self.parser.parse(response.content)

            logger.info(f"Classified query as '{result.type}' with confidence {result.confidence}")
            return result

        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            # Default to conversational with low confidence
            return QueryType(
                type="conversational",
                confidence=0.5,
                reasoning=f"Classification failed: {str(e)}"
            )
