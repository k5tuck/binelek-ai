"""
Kafka Consumers for AI Platform
Automatically update RAG knowledge base and recommendation engine
"""

from .entity_consumer import RAGKnowledgeBaseConsumer
from .relationship_consumer import RecommendationEngineConsumer

__all__ = ['RAGKnowledgeBaseConsumer', 'RecommendationEngineConsumer']
