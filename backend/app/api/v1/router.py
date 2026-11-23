"""
SupportPilot AI — API v1 Router
Mounts all v1 sub-routers in one place.
"""

from fastapi import APIRouter

from app.api.v1 import auth, tickets, agents, webhooks, analytics, knowledge, organizations

api_router = APIRouter()

# Version prefix
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth.router)
v1_router.include_router(organizations.router)
v1_router.include_router(tickets.router)
v1_router.include_router(knowledge.router)
v1_router.include_router(agents.router)
v1_router.include_router(webhooks.router)
v1_router.include_router(analytics.router)

api_router.include_router(v1_router)
