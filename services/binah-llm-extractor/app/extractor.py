"""
LLM Entity Extractor - Extracts structured entities from unstructured text.

This module uses LLMs (OpenAI, Anthropic, or Ollama) to extract entities
from unstructured data based on ontology schemas from binah-discovery.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import httpx

from .config import settings

logger = logging.getLogger(__name__)


class LLMEntityExtractor:
    """
    Extracts structured entities from unstructured data using LLM.

    Integrates with binah-discovery to fetch ontology schemas and ensure
    consistency between auto-discovered schemas and LLM-extracted entities.
    """

    def __init__(self):
        """Initialize LLM client based on configured provider."""
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL

        # Initialize LLM client
        if self.provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "ollama":
            self.client = AsyncOpenAI(
                base_url=settings.OLLAMA_BASE_URL,
                api_key="ollama"  # Ollama doesn't need real API key
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        # HTTP client for service communication
        self.discovery_client = httpx.AsyncClient(
            base_url=settings.DISCOVERY_SERVICE_URL,
            timeout=settings.REQUEST_TIMEOUT
        )

        logger.info(
            f"Initialized LLM extractor with provider={self.provider}, "
            f"model={self.model}"
        )

    async def extract_entities(
        self,
        raw_text: str,
        tenant_id: str,
        domain: str,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from unstructured text using LLM.

        Args:
            raw_text: Unstructured text (email, PDF content, etc.)
            tenant_id: Tenant identifier
            domain: Domain name (e.g., "real_estate")
            source_metadata: Optional metadata about the source

        Returns:
            List of extracted entities with confidence scores
        """
        try:
            # Step 1: Get existing ontology schema from binah-discovery
            # This ensures consistency with auto-discovered schema
            ontology_schema = await self._get_ontology_schema(tenant_id, domain)

            if not ontology_schema or not ontology_schema.get("entities"):
                logger.warning(
                    f"No ontology schema found for tenant={tenant_id}, "
                    f"domain={domain}. Cannot extract entities."
                )
                return []

            # Step 2: Build LLM prompt with schema
            system_prompt = self._build_system_prompt(ontology_schema)
            user_prompt = self._build_user_prompt(raw_text, source_metadata)

            # Step 3: Call LLM
            logger.debug(f"Calling LLM to extract entities from {len(raw_text)} chars")
            response_text = await self._call_llm(system_prompt, user_prompt)

            # Step 4: Parse and validate
            extracted = self._parse_llm_response(response_text)
            validated_entities = self._validate_against_schema(
                extracted.get("entities", []),
                ontology_schema
            )

            logger.info(
                f"Extracted {len(validated_entities)} entities from text "
                f"(tenant={tenant_id}, domain={domain})"
            )

            return validated_entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}", exc_info=True)
            return []

    async def _get_ontology_schema(
        self,
        tenant_id: str,
        domain: str
    ) -> Optional[Dict]:
        """
        Fetch current ontology schema from binah-discovery.

        This ensures LLM extraction uses the same schema as auto-discovery,
        maintaining consistency across structured and unstructured data.
        """
        try:
            response = await self.discovery_client.get(
                f"/api/ontology/{tenant_id}/current"
            )

            if response.status_code == 200:
                schema = response.json()
                logger.debug(
                    f"Fetched ontology schema for tenant={tenant_id}: "
                    f"{len(schema.get('entities', []))} entities"
                )
                return schema

            elif response.status_code == 404:
                logger.warning(
                    f"No ontology schema exists yet for tenant={tenant_id}. "
                    f"Create one using binah-discovery first."
                )
                return None

            else:
                logger.error(
                    f"Failed to fetch ontology schema: "
                    f"status={response.status_code}, body={response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error fetching ontology schema: {e}", exc_info=True)
            return None

    def _build_system_prompt(self, ontology_schema: Dict) -> str:
        """
        Build LLM system prompt using existing ontology schema.

        This maintains consistency between auto-discovery and LLM extraction.
        """
        entities = ontology_schema.get("entities", [])

        if not entities:
            return "You are a data extraction expert."

        entity_descriptions = []
        for entity in entities:
            attrs = entity.get("attributes", [])
            attr_list = ", ".join([
                f"{a['name']} ({a.get('type', 'string')}"
                f"{'*' if a.get('required') else ''})"
                for a in attrs
            ])

            entity_descriptions.append(
                f"- **{entity['name']}**: {entity.get('description', '')}\n"
                f"  Attributes: {attr_list}"
            )

        relationships_desc = ""
        if settings.ENABLE_RELATIONSHIP_EXTRACTION:
            relationships = ontology_schema.get("relationships", [])
            if relationships:
                rel_list = [
                    f"- {r['name']}: {r.get('from', '')} → {r.get('to', '')}"
                    for r in relationships
                ]
                relationships_desc = f"\n\n**Available Relationships:**\n" + "\n".join(rel_list)

        return f"""You are a data extraction expert. Extract structured entities from unstructured text according to the following ontology schema.

**Available Entity Types:**
{chr(10).join(entity_descriptions)}{relationships_desc}

**Instructions:**
1. Extract all entities that match the schema above
2. Use exact attribute names and types from the schema
3. Include a confidence score (0.0-1.0) for each entity
4. Only extract entities you're confident about (≥ {settings.MANUAL_REVIEW_THRESHOLD})
5. Do NOT invent new entity types or attributes not in the schema
6. Return ONLY valid JSON (no markdown, no explanations)

**Output Format:**
{{
    "entities": [
        {{
            "type": "EntityName",
            "attributes": {{
                "attributeName": "value",
                ...
            }},
            "confidence": 0.95
        }}
    ],
    "relationships": [
        {{
            "type": "RELATIONSHIP_NAME",
            "from_entity_index": 0,
            "to_entity_index": 1,
            "confidence": 0.9
        }}
    ]
}}

Extract entities now:"""

    def _build_user_prompt(
        self,
        raw_text: str,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build user prompt with raw text and optional metadata."""
        prompt = f"Extract entities from the following text:\n\n{raw_text}"

        if source_metadata:
            metadata_str = json.dumps(source_metadata, indent=2)
            prompt += f"\n\nSource Metadata:\n{metadata_str}"

        prompt += "\n\nReturn the extracted entities as JSON."
        return prompt

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM API based on configured provider."""
        try:
            if self.provider == "openai" or self.provider == "ollama":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=4096
                )
                return response.choices[0].message.content

            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=settings.LLM_TEMPERATURE
                )
                return response.content[0].text

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"LLM API call failed: {e}", exc_info=True)
            raise

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response to extract entities JSON."""
        try:
            # Handle markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            elif "{" in response_text:
                # Find JSON object in response
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_text = response_text[start:end]
            else:
                logger.warning("No JSON found in LLM response")
                return {"entities": [], "relationships": []}

            parsed = json.loads(json_text)

            if not isinstance(parsed, dict):
                logger.warning(f"LLM response is not a dict: {type(parsed)}")
                return {"entities": [], "relationships": []}

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            return {"entities": [], "relationships": []}

    def _validate_against_schema(
        self,
        entities: List[Dict],
        schema: Dict
    ) -> List[Dict]:
        """
        Validate extracted entities against ontology schema.

        Ensures LLM output matches auto-discovered schema.
        """
        validated = []
        schema_map = {e["name"]: e for e in schema.get("entities", [])}

        for entity in entities:
            entity_type = entity.get("type")

            # Check entity type exists in schema
            if entity_type not in schema_map:
                logger.warning(f"Unknown entity type: {entity_type} (not in schema)")
                continue

            entity_schema = schema_map[entity_type]
            required_attrs = [
                a["name"] for a in entity_schema.get("attributes", [])
                if a.get("required", False)
            ]

            # Check required attributes
            entity_attrs = entity.get("attributes", {})
            missing = [
                attr for attr in required_attrs
                if attr not in entity_attrs
            ]

            if missing:
                # Reduce confidence if missing required fields
                original_confidence = entity.get("confidence", 1.0)
                penalty = 0.7  # 30% penalty
                entity["confidence"] = original_confidence * penalty
                logger.debug(
                    f"Entity {entity_type} missing required attributes: {missing}. "
                    f"Reduced confidence to {entity['confidence']:.2f}"
                )

            # Type validation
            for attr_name, attr_value in entity_attrs.items():
                schema_attr = next(
                    (a for a in entity_schema.get("attributes", [])
                     if a["name"] == attr_name),
                    None
                )
                if schema_attr:
                    expected_type = schema_attr.get("type", "string")
                    if not self._validate_type(attr_value, expected_type):
                        logger.warning(
                            f"Type mismatch for {entity_type}.{attr_name}: "
                            f"expected {expected_type}, got {type(attr_value).__name__}"
                        )

            validated.append(entity)

        return validated

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value matches expected type."""
        type_map = {
            "string": str,
            "int": int,
            "integer": int,
            "decimal": (int, float),
            "float": float,
            "money": (int, float),
            "bool": bool,
            "boolean": bool,
            "date": str,  # Dates are strings in ISO format
            "datetime": str,
            "guid": str,
            "uuid": str,
            "enum": str,
        }

        expected_python_type = type_map.get(expected_type.lower(), str)
        return isinstance(value, expected_python_type)

    async def close(self):
        """Clean up resources."""
        await self.discovery_client.aclose()
        logger.info("LLM extractor closed")
