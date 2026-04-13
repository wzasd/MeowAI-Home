from fastapi import Request
from src.thread import ThreadManager
from src.router.agent_router_v2 import AgentRouterV2
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.config.runtime_catalog import RuntimeCatalog, get_runtime_catalog
from src.session.chain import SessionChain


def get_thread_manager(request: Request) -> ThreadManager:
    return request.app.state.thread_manager


def get_agent_router(request: Request) -> AgentRouterV2:
    return request.app.state.agent_router


def get_cat_registry(request: Request) -> CatRegistry:
    return request.app.state.cat_registry


def get_agent_registry(request: Request) -> AgentRegistry:
    return request.app.state.agent_registry


def get_runtime_catalog_dep(request: Request) -> RuntimeCatalog:
    """Get runtime catalog instance."""
    return get_runtime_catalog()


def get_session_chain(request: Request) -> SessionChain:
    """Get session chain instance."""
    return request.app.state.session_chain
