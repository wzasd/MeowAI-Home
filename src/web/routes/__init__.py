# Route modules for MeowAI Home API
from src.web.routes.packs import router as packs_router
from src.web.routes.agents import router as agents_router
from src.web.routes.memory import router as memory_router
from src.web.routes.skills_api import router as skills_router
from src.web.routes.governance import router as governance_router
from src.web.routes.workflow import router as workflow_router

__all__ = [
    "packs_router",
    "agents_router",
    "memory_router",
    "skills_router",
    "governance_router",
    "workflow_router",
]
