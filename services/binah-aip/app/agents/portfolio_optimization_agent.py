"""Portfolio Optimization Agent - Specialized agent for portfolio analysis and optimization"""

from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Any, Literal
from uuid import UUID
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PortfolioOptimizationRequest(BaseModel):
    """Request for portfolio optimization"""
    portfolio_id: UUID | None = None
    tenant_id: UUID
    property_ids: list[UUID] | None = None
    objective: Literal["maximize_roi", "minimize_risk", "balanced", "cash_flow", "appreciation"] = "balanced"
    constraints: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None


class PropertyRecommendation(BaseModel):
    """Individual property recommendation"""
    property_id: UUID
    action: Literal["acquire", "hold", "sell", "improve"]
    priority: Literal["high", "medium", "low"]
    reasoning: str
    expected_impact: dict[str, Any]
    estimated_cost: float | None = None
    estimated_return: float | None = None
    timeframe: str


class PortfolioOptimizationResponse(BaseModel):
    """Response from portfolio optimization"""
    portfolio_id: UUID | None
    tenant_id: UUID
    objective: str
    current_metrics: dict[str, Any]
    optimized_metrics: dict[str, Any]
    recommendations: list[PropertyRecommendation]
    diversification_score: float = Field(ge=0.0, le=10.0)
    risk_score: float = Field(ge=0.0, le=10.0)
    expected_roi_improvement: float
    summary: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PortfolioOptimizationAgent:
    """
    Specialized agent for portfolio analysis and optimization

    Capabilities:
    - Portfolio performance analysis
    - Diversification assessment
    - Risk-return optimization
    - Acquisition recommendations
    - Disposition recommendations
    - Asset allocation optimization
    - Rebalancing strategies
    """

    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever

        self.optimization_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a real estate portfolio optimization expert with expertise in modern portfolio theory.

Your task is to analyze and optimize real estate portfolios based on objectives:

1. **maximize_roi**: Maximize return on investment
   - Identify highest ROI properties to acquire
   - Identify underperforming properties to sell
   - Recommend value-add improvements
   - Optimize capital allocation

2. **minimize_risk**: Minimize portfolio risk
   - Diversify by geography, property type, tenant mix
   - Reduce concentration risk
   - Hedge against market downturns
   - Reduce leverage where appropriate

3. **balanced**: Balance risk and return (Sharpe ratio optimization)
   - Efficient frontier analysis
   - Risk-adjusted returns
   - Optimal asset allocation

4. **cash_flow**: Maximize cash flow and income
   - High-yield properties
   - Stable, predictable income
   - Minimize vacancy and turnover

5. **appreciation**: Maximize long-term appreciation
   - Growth markets
   - Value-add opportunities
   - Development potential

Portfolio Metrics:
- Total portfolio value
- Weighted average ROI
- Cash-on-cash return
- Diversification (Herfindahl index)
- Geographic concentration
- Property type concentration
- Risk score (based on volatility, leverage, market risk)

For each recommendation:
- Action (acquire, hold, sell, improve)
- Priority (high, medium, low)
- Reasoning and expected impact
- Cost and expected return
- Timeframe

Overall optimization:
- Current vs optimized metrics
- Expected ROI improvement
- Risk reduction
- Confidence level"""),
            ("user", """Optimize this portfolio:

Portfolio ID: {portfolio_id}
Objective: {objective}

Current Portfolio:
{portfolio_data}

Property Details:
{property_details}

Market Data:
{market_data}

Constraints:
{constraints}

Parameters:
{parameters}

Provide your optimization plan as JSON:
{{
  "current_metrics": {{
    "total_value": 15000000,
    "weighted_avg_roi": 8.5,
    "cash_flow": 750000,
    "diversification_score": 6.2,
    "risk_score": 5.8
  }},
  "optimized_metrics": {{
    "total_value": 16500000,
    "weighted_avg_roi": 11.2,
    "cash_flow": 900000,
    "diversification_score": 8.1,
    "risk_score": 4.3
  }},
  "recommendations": [
    {{
      "property_id": "uuid",
      "action": "sell",
      "priority": "high",
      "reasoning": "Underperforming asset with declining market",
      "expected_impact": {{"roi_increase": 2.5, "risk_decrease": 1.2}},
      "estimated_cost": 0,
      "estimated_return": 850000,
      "timeframe": "3-6 months"
    }},
    {{
      "property_id": "uuid",
      "action": "acquire",
      "priority": "high",
      "reasoning": "High-growth market with strong fundamentals",
      "expected_impact": {{"roi_increase": 3.2, "diversification_increase": 1.5}},
      "estimated_cost": 1200000,
      "estimated_return": 1850000,
      "timeframe": "5 years"
    }}
  ],
  "diversification_score": 8.1,
  "risk_score": 4.3,
  "expected_roi_improvement": 2.7,
  "summary": "...",
  "confidence": <0-1>
}}""")
        ])

    async def optimize_portfolio(
        self,
        request: PortfolioOptimizationRequest
    ) -> PortfolioOptimizationResponse:
        """
        Optimize a real estate portfolio

        Args:
            request: PortfolioOptimizationRequest with portfolio and objective

        Returns:
            PortfolioOptimizationResponse with optimization plan
        """
        try:
            # Step 1: Gather portfolio data
            portfolio_data = await self._get_portfolio_data(
                request.portfolio_id,
                request.tenant_id
            )

            # Step 2: Gather property details
            property_ids = request.property_ids or portfolio_data.get("property_ids", [])
            property_details = await self._get_property_details(
                property_ids,
                request.tenant_id
            )

            # Step 3: Gather market data
            market_data = await self._get_market_data_for_properties(
                property_details,
                request.tenant_id
            )

            # Step 4: Run optimization with LLM
            prompt = self.optimization_prompt.format_messages(
                portfolio_id=str(request.portfolio_id) if request.portfolio_id else "N/A",
                objective=request.objective,
                portfolio_data=str(portfolio_data),
                property_details=str(property_details)[:3000],  # Limit size
                market_data=str(market_data)[:2000],
                constraints=str(request.constraints or {}),
                parameters=str(request.parameters or {})
            )

            response = await self.llm.ainvoke(prompt)

            # Parse response
            import json
            try:
                result_data = json.loads(response.content)

                # Convert recommendations to PropertyRecommendation objects
                recommendations = []
                for rec in result_data.get("recommendations", []):
                    try:
                        recommendations.append(PropertyRecommendation(**rec))
                    except Exception as rec_error:
                        logger.warning(f"Error parsing recommendation: {rec_error}")
                        continue

            except Exception as parse_error:
                logger.warning(f"Error parsing optimization response: {parse_error}")
                # Fallback
                recommendations = []
                result_data = {
                    "current_metrics": {},
                    "optimized_metrics": {},
                    "diversification_score": 5.0,
                    "risk_score": 5.0,
                    "expected_roi_improvement": 0.0,
                    "summary": "Optimization analysis incomplete",
                    "confidence": 0.5
                }

            return PortfolioOptimizationResponse(
                portfolio_id=request.portfolio_id,
                tenant_id=request.tenant_id,
                objective=request.objective,
                current_metrics=result_data.get("current_metrics", {}),
                optimized_metrics=result_data.get("optimized_metrics", {}),
                recommendations=recommendations,
                diversification_score=result_data.get("diversification_score", 5.0),
                risk_score=result_data.get("risk_score", 5.0),
                expected_roi_improvement=result_data.get("expected_roi_improvement", 0.0),
                summary=result_data.get("summary", ""),
                confidence=result_data.get("confidence", 0.7)
            )

        except Exception as e:
            logger.error(f"Portfolio optimization error: {e}")
            return PortfolioOptimizationResponse(
                portfolio_id=request.portfolio_id,
                tenant_id=request.tenant_id,
                objective=request.objective,
                current_metrics={},
                optimized_metrics={},
                recommendations=[],
                diversification_score=0.0,
                risk_score=10.0,
                expected_roi_improvement=0.0,
                summary=f"Optimization failed: {str(e)}",
                confidence=0.0
            )

    async def _get_portfolio_data(
        self,
        portfolio_id: UUID | None,
        tenant_id: UUID
    ) -> dict:
        """Retrieve portfolio summary data"""
        try:
            # Query Neo4j for portfolio
            return {
                "id": str(portfolio_id) if portfolio_id else None,
                "name": "Main Portfolio",
                "total_value": 15000000,
                "num_properties": 8,
                "property_ids": [
                    "prop-1", "prop-2", "prop-3", "prop-4",
                    "prop-5", "prop-6", "prop-7", "prop-8"
                ],
                "total_units": 186,
                "occupancy_rate": 92.5,
                "annual_revenue": 2850000,
                "noi": 1710000
            }
        except Exception as e:
            logger.error(f"Error fetching portfolio data: {e}")
            return {}

    async def _get_property_details(
        self,
        property_ids: list,
        tenant_id: UUID
    ) -> list[dict]:
        """Retrieve detailed property data"""
        try:
            # Query Neo4j for each property
            # Placeholder
            return [
                {
                    "id": prop_id,
                    "address": f"{prop_id} Main St",
                    "property_type": "Multifamily",
                    "value": 1875000,
                    "roi": 8.5,
                    "risk_score": 5.5,
                    "market": "Austin, TX"
                }
                for prop_id in property_ids[:10]  # Limit to 10
            ]
        except Exception as e:
            logger.error(f"Error fetching property details: {e}")
            return []

    async def _get_market_data_for_properties(
        self,
        properties: list[dict],
        tenant_id: UUID
    ) -> dict:
        """Retrieve market data for property locations"""
        try:
            # Get unique markets
            markets = list(set(p.get("market") for p in properties if p.get("market")))

            # Query market data for each
            market_data = {}
            for market in markets:
                market_data[market] = {
                    "price_trend": 5.2,
                    "market_health": "hot",
                    "risk_level": "low"
                }

            return market_data
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return {}

    async def calculate_diversification_score(
        self,
        portfolio_data: dict
    ) -> float:
        """
        Calculate portfolio diversification score using Herfindahl index

        Args:
            portfolio_data: Portfolio data with property allocations

        Returns:
            Diversification score 0-10 (higher = more diversified)
        """
        try:
            # Calculate Herfindahl index for concentration
            # H = sum of squared market shares
            # Diversification score = 10 * (1 - normalized H)

            # Simplified calculation - would use actual property values
            num_properties = portfolio_data.get("num_properties", 1)

            # Perfect diversification = each property is 1/n of portfolio
            # Complete concentration = one property is 100%
            if num_properties <= 1:
                return 0.0

            # Assuming equal weight for now (would calculate actual)
            herfindahl = 1.0 / num_properties
            max_herfindahl = 1.0  # Complete concentration
            normalized_h = herfindahl / max_herfindahl

            diversification_score = 10.0 * (1.0 - normalized_h)

            return min(10.0, max(0.0, diversification_score))

        except Exception as e:
            logger.error(f"Error calculating diversification: {e}")
            return 5.0

    async def generate_optimization_report(
        self,
        optimization_response: PortfolioOptimizationResponse
    ) -> str:
        """
        Generate formatted optimization report

        Args:
            optimization_response: PortfolioOptimizationResponse to format

        Returns:
            Formatted report as markdown
        """
        report = f"""# Portfolio Optimization Report

**Objective:** {optimization_response.objective.replace('_', ' ').title()}
**Date:** {optimization_response.timestamp.strftime('%Y-%m-%d')}
**Confidence:** {optimization_response.confidence * 100:.1f}%

## Executive Summary

{optimization_response.summary}

**Expected ROI Improvement:** +{optimization_response.expected_roi_improvement:.2f}%

## Current vs Optimized Metrics

| Metric | Current | Optimized | Change |
|--------|---------|-----------|--------|
"""
        current = optimization_response.current_metrics
        optimized = optimization_response.optimized_metrics

        for key in current.keys():
            curr_val = current.get(key, 0)
            opt_val = optimized.get(key, 0)

            if isinstance(curr_val, (int, float)):
                change = opt_val - curr_val
                change_pct = (change / curr_val * 100) if curr_val != 0 else 0
                report += f"| {key.replace('_', ' ').title()} | {curr_val:,.2f} | {opt_val:,.2f} | {change:+,.2f} ({change_pct:+.1f}%) |\n"

        report += f"""
**Diversification Score:** {optimization_response.diversification_score:.1f}/10
**Risk Score:** {optimization_response.risk_score:.1f}/10

## Recommendations ({len(optimization_response.recommendations)})

"""
        # Group by action
        high_priority = [r for r in optimization_response.recommendations if r.priority == "high"]
        medium_priority = [r for r in optimization_response.recommendations if r.priority == "medium"]
        low_priority = [r for r in optimization_response.recommendations if r.priority == "low"]

        if high_priority:
            report += "### High Priority\n\n"
            for rec in high_priority:
                report += f"**{rec.action.upper()}: Property {rec.property_id}**\n"
                report += f"- {rec.reasoning}\n"
                report += f"- Expected Impact: {rec.expected_impact}\n"
                if rec.estimated_cost:
                    report += f"- Cost: ${rec.estimated_cost:,.2f}\n"
                if rec.estimated_return:
                    report += f"- Return: ${rec.estimated_return:,.2f}\n"
                report += f"- Timeframe: {rec.timeframe}\n\n"

        if medium_priority:
            report += "### Medium Priority\n\n"
            for rec in medium_priority:
                report += f"**{rec.action.upper()}: Property {rec.property_id}** - {rec.reasoning}\n\n"

        if low_priority:
            report += "### Low Priority\n\n"
            for rec in low_priority:
                report += f"- {rec.action.upper()}: Property {rec.property_id}\n"

        return report
