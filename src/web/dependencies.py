from fastapi import Request
from src.thread import ThreadManager
from src.router.agent_router_v2 import AgentRouterV2
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry


def get_thread_manager(request: Request) -> ThreadManager:
    return request.app.state.thread_manager


def get_agent_router(request: Request) -> AgentRouterV2:
    return request.app.state.agent_router


def get_cat_registry(request: Request) -> CatRegistry:
    return request.app.state.cat_registry


def get_agent_registry(request: Request) -> AgentRegistry:
    return request.app.state.agent_registry
