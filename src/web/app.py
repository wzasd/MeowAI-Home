from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.thread import ThreadManager
from src.router.agent_router_v2 import AgentRouterV2
from src.models.registry_init import initialize_registries
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.session.chain import SessionChain
from src.invocation.tracker import InvocationTracker
from src.memory import MemoryService
from src.web.routes.threads import router as threads_router
from src.web.routes.messages import router as messages_router
from src.web.routes.ws import router as ws_router
from src.web.routes.monitoring import router as monitoring_router
from src.web.routes.queue import router as queue_router
from src.web.routes.metrics import router as metrics_router
from src.web.routes.tasks import router as tasks_router
from src.web.routes.missions import router as missions_router
from src.web.routes.connectors_messages import router as connectors_messages_router
from src.web.routes.audit import router as audit_router
from src.web.routes.signals import router as signals_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        cat_reg, agent_reg = initialize_registries("cat-config.json")
    except (FileNotFoundError, Exception):
        cat_reg, agent_reg = CatRegistry(), AgentRegistry()

    app.state.cat_registry = cat_reg
    app.state.agent_registry = agent_reg
    app.state.agent_router = AgentRouterV2(cat_reg, agent_reg)
    app.state.session_chain = SessionChain()
    app.state.invocation_tracker = InvocationTracker()
    app.state.memory_service = MemoryService()

    tm = ThreadManager(skip_init=True)
    await tm.async_init()
    app.state.thread_manager = tm

    yield

    if hasattr(tm, '_store') and tm._store:
        await tm._store.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MeowAI Home",
        version="0.8.0",
        description="Multi-Agent AI Collaboration Platform",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    from src.web.routes.cats import router as cats_router
    from src.web.routes.config import router as config_router
    from src.web.routes.connectors import router as connectors_router
    from src.web.routes.workspace import router as workspace_router

    app.include_router(threads_router, prefix="/api")
    app.include_router(messages_router, prefix="/api")
    app.include_router(ws_router)
    app.include_router(monitoring_router)
    app.include_router(cats_router, prefix="/api")
    app.include_router(config_router, prefix="/api")
    app.include_router(connectors_router, prefix="/api")
    app.include_router(workspace_router, prefix="/api")
    app.include_router(queue_router, prefix="/api")
    app.include_router(metrics_router)
    app.include_router(tasks_router, prefix="/api")
    app.include_router(missions_router, prefix="/api")
    app.include_router(connectors_messages_router, prefix="/api")
    app.include_router(audit_router)
    app.include_router(signals_router, prefix="/api")

    # Mount packs routes if available
    try:
        from src.web.routes.packs import router as packs_router
        app.include_router(packs_router, prefix="/api")
    except ImportError:
        pass

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.8.0"}

    web_dist = Path(__file__).parent.parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/{path:path}")
        async def serve_spa(path: str):
            index_file = web_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"error": "Frontend not built"}

    return app
