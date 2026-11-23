"""
SupportPilot AI — Analytics Pydantic Schemas
Defines structured responses for real PostgreSQL organization-scoped metrics.
"""

from pydantic import BaseModel, Field


class AnalyticsOverviewResponse(BaseModel):
    total_tickets: int = Field(default=0, description="Total ticket volume in organization")
    open_tickets: int = Field(default=0, description="Tickets currently open, assigned, or in progress")
    resolved_tickets: int = Field(default=0, description="Total resolved or closed tickets")
    escalated_tickets: int = Field(default=0, description="Tickets currently in escalated state")
    ai_resolved_tickets: int = Field(default=0, description="Tickets resolved autonomously by AI without human assignment")
    human_resolved_tickets: int = Field(default=0, description="Tickets resolved with human agent intervention")
    escalation_rate: float = Field(default=0.0, description="Percentage of tickets requiring human escalation")
    avg_first_response_time_seconds: float | None = Field(default=None, description="Average seconds until first agent or AI response")
    avg_resolution_time_seconds: float | None = Field(default=None, description="Average seconds from creation to resolution")
    csat_score: float | None = Field(default=None, description="Average Customer Satisfaction Score (1.0 to 5.0)")
    csat_total_feedback: int = Field(default=0, description="Total number of survey responses received")
    csat_positive_rate: float | None = Field(default=None, description="Percentage of ratings with 4 or 5 stars")
    category_distribution: dict[str, int] = Field(default_factory=dict, description="Ticket count breakdown by AI category")
    priority_distribution: dict[str, int] = Field(default_factory=dict, description="Ticket count breakdown by priority")
    status_distribution: dict[str, int] = Field(default_factory=dict, description="Ticket count breakdown by state")
