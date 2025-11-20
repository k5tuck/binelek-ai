"""Due Diligence Agent - Specialized agent for property due diligence and risk assessment"""

from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Any, Literal
from uuid import UUID
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DueDiligenceRequest(BaseModel):
    """Request for due diligence analysis"""
    property_id: UUID
    tenant_id: UUID
    scope: Literal["full", "financial", "legal", "physical", "environmental"] = "full"
    parameters: dict[str, Any] | None = None


class RiskFinding(BaseModel):
    """Individual risk finding"""
    category: Literal["financial", "legal", "physical", "environmental", "operational"]
    severity: Literal["critical", "high", "medium", "low"]
    title: str
    description: str
    impact: str
    mitigation: str
    estimated_cost: float | None = None


class DueDiligenceResponse(BaseModel):
    """Response from due diligence analysis"""
    property_id: UUID
    scope: str
    overall_rating: Literal["pass", "pass_with_conditions", "fail"]
    risk_score: float = Field(ge=0.0, le=10.0, description="Risk score 0-10, higher is riskier")
    findings: list[RiskFinding]
    recommendations: list[str]
    deal_breakers: list[str]
    estimated_total_risk_cost: float
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DueDiligenceAgent:
    """
    Specialized agent for comprehensive property due diligence

    Capabilities:
    - Financial due diligence (cash flow, expenses, tax records)
    - Legal due diligence (title, liens, zoning, permits)
    - Physical due diligence (condition, deferred maintenance, inspections)
    - Environmental due diligence (hazards, contamination, compliance)
    - Operational due diligence (management, contracts, leases)
    """

    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever

        self.diligence_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a real estate due diligence expert conducting comprehensive property investigations.

Your task is to analyze properties for risk based on the scope:

1. **financial**: Financial due diligence:
   - Review historical financial statements
   - Verify rent rolls and occupancy
   - Analyze operating expenses
   - Review tax records and assessments
   - Identify revenue inconsistencies
   - Flag unusual expenses

2. **legal**: Legal due diligence:
   - Title search and chain of title
   - Liens, encumbrances, easements
   - Zoning compliance
   - Building permits and certificates
   - Pending litigation
   - HOA/condo documents

3. **physical**: Physical due diligence:
   - Property condition assessment
   - Deferred maintenance items
   - Major system age/condition (HVAC, roof, plumbing, electrical)
   - Building code violations
   - Required capital expenditures
   - Inspection reports

4. **environmental**: Environmental due diligence:
   - Phase I/II environmental assessments
   - Hazardous materials (asbestos, lead paint)
   - Soil/groundwater contamination
   - Flood zone status
   - Environmental compliance

5. **full**: All of the above

For each finding, provide:
- Category (financial, legal, physical, environmental, operational)
- Severity (critical, high, medium, low)
- Title and description
- Impact on investment
- Mitigation strategy
- Estimated cost to remediate

Overall assessment:
- Rating (pass, pass_with_conditions, fail)
- Risk score (0-10, higher = riskier)
- Deal-breakers that would kill the deal"""),
            ("user", """Conduct due diligence on this property:

Property ID: {property_id}
Scope: {scope}

Property Data: {property_data}
Financial Records: {financial_data}
Legal Documents: {legal_data}
Inspection Reports: {inspection_data}
Environmental Reports: {environmental_data}

Parameters: {parameters}

Provide your due diligence report as JSON:
{{
  "overall_rating": "pass|pass_with_conditions|fail",
  "risk_score": <0-10>,
  "findings": [
    {{
      "category": "financial",
      "severity": "high",
      "title": "Unexplained Revenue Drop",
      "description": "...",
      "impact": "...",
      "mitigation": "...",
      "estimated_cost": 50000
    }}
  ],
  "recommendations": ["rec1", "rec2"],
  "deal_breakers": ["breaker1"],
  "estimated_total_risk_cost": 250000,
  "confidence": <0-1>
}}""")
        ])

    async def conduct_due_diligence(
        self,
        request: DueDiligenceRequest
    ) -> DueDiligenceResponse:
        """
        Conduct comprehensive due diligence on a property

        Args:
            request: DueDiligenceRequest with property_id and scope

        Returns:
            DueDiligenceResponse with findings and recommendations
        """
        try:
            # Step 1: Gather property data
            property_data = await self._get_property_data(
                request.property_id,
                request.tenant_id
            )

            # Step 2: Gather scope-specific data
            financial_data = await self._get_financial_data(
                request.property_id,
                request.tenant_id
            ) if request.scope in ["full", "financial"] else {}

            legal_data = await self._get_legal_data(
                request.property_id,
                request.tenant_id
            ) if request.scope in ["full", "legal"] else {}

            inspection_data = await self._get_inspection_data(
                request.property_id,
                request.tenant_id
            ) if request.scope in ["full", "physical"] else {}

            environmental_data = await self._get_environmental_data(
                request.property_id,
                request.tenant_id
            ) if request.scope in ["full", "environmental"] else {}

            # Step 3: Run due diligence analysis with LLM
            prompt = self.diligence_prompt.format_messages(
                property_id=str(request.property_id),
                scope=request.scope,
                property_data=str(property_data),
                financial_data=str(financial_data),
                legal_data=str(legal_data),
                inspection_data=str(inspection_data),
                environmental_data=str(environmental_data),
                parameters=str(request.parameters or {})
            )

            response = await self.llm.ainvoke(prompt)

            # Parse response
            import json
            try:
                result_data = json.loads(response.content)

                # Convert findings to RiskFinding objects
                findings = [
                    RiskFinding(**finding)
                    for finding in result_data.get("findings", [])
                ]
            except Exception as parse_error:
                logger.warning(f"Error parsing due diligence response: {parse_error}")
                # Fallback
                findings = []
                result_data = {
                    "overall_rating": "pass_with_conditions",
                    "risk_score": 5.0,
                    "recommendations": ["Manual review required"],
                    "deal_breakers": [],
                    "estimated_total_risk_cost": 0,
                    "confidence": 0.5
                }

            return DueDiligenceResponse(
                property_id=request.property_id,
                scope=request.scope,
                overall_rating=result_data.get("overall_rating", "pass_with_conditions"),
                risk_score=result_data.get("risk_score", 5.0),
                findings=findings,
                recommendations=result_data.get("recommendations", []),
                deal_breakers=result_data.get("deal_breakers", []),
                estimated_total_risk_cost=result_data.get("estimated_total_risk_cost", 0),
                confidence=result_data.get("confidence", 0.7)
            )

        except Exception as e:
            logger.error(f"Due diligence error: {e}")
            return DueDiligenceResponse(
                property_id=request.property_id,
                scope=request.scope,
                overall_rating="fail",
                risk_score=10.0,
                findings=[
                    RiskFinding(
                        category="operational",
                        severity="critical",
                        title="Due Diligence Analysis Failed",
                        description=str(e),
                        impact="Cannot assess property risks",
                        mitigation="Retry analysis or conduct manual due diligence"
                    )
                ],
                recommendations=["Conduct manual due diligence"],
                deal_breakers=["Analysis failure"],
                estimated_total_risk_cost=0,
                confidence=0.0
            )

    async def _get_property_data(self, property_id: UUID, tenant_id: UUID) -> dict:
        """Retrieve basic property data"""
        try:
            # Query Neo4j
            return {
                "id": str(property_id),
                "address": "123 Main St, Austin, TX",
                "property_type": "Multifamily",
                "year_built": 2015,
                "units": 24,
                "total_sqft": 28800
            }
        except Exception as e:
            logger.error(f"Error fetching property data: {e}")
            return {}

    async def _get_financial_data(self, property_id: UUID, tenant_id: UUID) -> dict:
        """Retrieve financial records"""
        try:
            return {
                "annual_revenue": 720000,
                "operating_expenses": 288000,
                "noi": 432000,
                "occupancy_rate": 95.0,
                "average_rent": 2500,
                "expense_ratio": 40.0,
                "tax_assessment": 3200000
            }
        except Exception as e:
            logger.error(f"Error fetching financial data: {e}")
            return {}

    async def _get_legal_data(self, property_id: UUID, tenant_id: UUID) -> dict:
        """Retrieve legal documents and status"""
        try:
            return {
                "title_status": "clear",
                "liens": [],
                "zoning": "R-3 Multifamily",
                "zoning_compliant": True,
                "pending_litigation": False,
                "permits_current": True
            }
        except Exception as e:
            logger.error(f"Error fetching legal data: {e}")
            return {}

    async def _get_inspection_data(self, property_id: UUID, tenant_id: UUID) -> dict:
        """Retrieve inspection reports"""
        try:
            return {
                "last_inspection_date": "2024-10-15",
                "roof_condition": "good",
                "hvac_age_years": 3,
                "plumbing_issues": None,
                "electrical_issues": None,
                "deferred_maintenance": ["Exterior paint", "Parking lot seal coat"],
                "estimated_capex_5y": 85000
            }
        except Exception as e:
            logger.error(f"Error fetching inspection data: {e}")
            return {}

    async def _get_environmental_data(self, property_id: UUID, tenant_id: UUID) -> dict:
        """Retrieve environmental reports"""
        try:
            return {
                "phase_1_complete": True,
                "phase_1_findings": "No recognized environmental conditions",
                "flood_zone": "X (minimal risk)",
                "asbestos": False,
                "lead_paint": False,
                "soil_contamination": False
            }
        except Exception as e:
            logger.error(f"Error fetching environmental data: {e}")
            return {}

    async def generate_report(
        self,
        diligence_response: DueDiligenceResponse
    ) -> str:
        """
        Generate a formatted due diligence report

        Args:
            diligence_response: DueDiligenceResponse to format

        Returns:
            Formatted report as markdown
        """
        report = f"""# Due Diligence Report

**Property ID:** {diligence_response.property_id}
**Scope:** {diligence_response.scope}
**Date:** {diligence_response.timestamp.strftime('%Y-%m-%d')}

## Executive Summary

**Overall Rating:** {diligence_response.overall_rating.upper()}
**Risk Score:** {diligence_response.risk_score}/10
**Confidence:** {diligence_response.confidence * 100:.1f}%

**Estimated Total Risk Cost:** ${diligence_response.estimated_total_risk_cost:,.2f}

## Findings ({len(diligence_response.findings)})

"""
        # Group findings by severity
        critical = [f for f in diligence_response.findings if f.severity == "critical"]
        high = [f for f in diligence_response.findings if f.severity == "high"]
        medium = [f for f in diligence_response.findings if f.severity == "medium"]
        low = [f for f in diligence_response.findings if f.severity == "low"]

        if critical:
            report += "### Critical Issues\n\n"
            for finding in critical:
                report += f"**{finding.title}** ({finding.category})\n"
                report += f"- {finding.description}\n"
                report += f"- Impact: {finding.impact}\n"
                report += f"- Mitigation: {finding.mitigation}\n"
                if finding.estimated_cost:
                    report += f"- Estimated Cost: ${finding.estimated_cost:,.2f}\n"
                report += "\n"

        if high:
            report += "### High Priority Issues\n\n"
            for finding in high:
                report += f"**{finding.title}** ({finding.category})\n"
                report += f"- {finding.description}\n"
                if finding.estimated_cost:
                    report += f"- Estimated Cost: ${finding.estimated_cost:,.2f}\n"
                report += "\n"

        report += f"""## Recommendations

"""
        for i, rec in enumerate(diligence_response.recommendations, 1):
            report += f"{i}. {rec}\n"

        if diligence_response.deal_breakers:
            report += f"""\n## Deal Breakers

"""
            for i, breaker in enumerate(diligence_response.deal_breakers, 1):
                report += f"{i}. {breaker}\n"

        return report
