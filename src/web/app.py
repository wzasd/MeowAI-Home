import os
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
from src.auth.store import AuthStore
from src.auth.middleware import AuthMiddleware
from src.scheduler.runner import TaskRunner, TaskGovernance
from src.scheduler.pipeline import Pipeline, ActorResolver
from src.review.watcher import ReviewWatcher
from src.review.router import ReviewRouterBuilder
from src.review.thread_router import ThreadRouter
from src.review.ci_tracker import CITracker
from src.limb import LimbRegistry, LeaseManager
from src.web.routes.threads import router as threads_router
from src.web.routes.messages import router as messages_router
from src.web.routes.ws import router as ws_router
from src.web.routes.monitoring import router as monitoring_router
from src.web.routes.queue import router as queue_router
from src.web.routes.metrics import router as metrics_router
from src.web.routes.tasks import router as tasks_router
from src.web.routes.missions import router as missions_router
from src.web.routes.connectors_messages import router as connectors_messages_router
from src.web.routes.evidence import router as evidence_router
from src.web.routes.uploads import router as uploads_router
from src.web.routes.audit import router as audit_router
from src.web.routes.signals import router as signals_router
from src.web.routes.sessions import router as sessions_router
from src.web.routes.governance import router as governance_router
from src.web.routes.capabilities import router as capabilities_router
from src.web.routes.voice import router as voice_router
from src.web.routes.scheduler import router as scheduler_router
from src.web.routes.review import router as review_router
from src.web.routes.workflow import router as workflow_router
from src.web.routes.limbs import router as limbs_router


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

    auth_store = AuthStore()
    await auth_store.initialize()
    app.state.auth_store = auth_store

    tm = ThreadManager(skip_init=True)
    await tm.async_init()
    app.state.thread_manager = tm

    # Initialize scheduler
    task_governance = TaskGovernance()
    task_runner = TaskRunner(db_path="data/scheduler.db", governance=task_governance)
    app.state.task_runner = task_runner

    # Initialize scheduler pipeline
    actor_resolver = ActorResolver(cat_registry=cat_reg)
    scheduler_pipeline = Pipeline(actor_resolver=actor_resolver, governance=task_governance)
    app.state.scheduler_pipeline = scheduler_pipeline

    # Register default executors for templates
    from src.scheduler.templates import SCHEDULER_TEMPLATES
    for tmpl in SCHEDULER_TEMPLATES:
        async def _default_executor(context):
            pass
        scheduler_pipeline.register_executor(tmpl["id"], _default_executor)

    # Initialize review system
    review_watcher = ReviewWatcher(webhook_secret=os.environ.get("GITHUB_WEBHOOK_SECRET"))
    app.state.review_watcher = review_watcher
    app.state.review_router = ReviewRouterBuilder.create_default_router()
    app.state.review_thread_router = ThreadRouter(tm)
    ci_tracker = CITracker(poll_interval=120)
    app.state.ci_tracker = ci_tracker
    await ci_tracker.start()

    # Initialize limb control plane
    lease_manager = LeaseManager()
    limb_registry = LimbRegistry(db_path="data/limb_registry.db", lease_manager=lease_manager)
    app.state.limb_registry = limb_registry
    app.state.limb_lease_manager = lease_manager

    # Start task runner
    await task_runner.start()

    yield

    if hasattr(tm, '_store') and tm._store:
        await tm._store.close()
    if hasattr(app.state, 'auth_store') and app.state.auth_store:
        await app.state.auth_store.close()
    if hasattr(app.state, 'task_runner') and app.state.task_runner:
        await app.state.task_runner.stop()
    if hasattr(app.state, 'ci_tracker') and app.state.ci_tracker:
        await app.state.ci_tracker.stop()
    imap_poller = getattr(app.state, 'imap_poller', None)
    if imap_poller:
        await imap_poller.stop()


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

    from src.web.routes.auth import router as auth_router
    from src.web.routes.cats import router as cats_router
    from src.web.routes.config import router as config_router
    from src.web.routes.connectors import router as connectors_router
    from src.web.routes.workspace import router as workspace_router

    app.include_router(auth_router, prefix="/api")
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
    app.include_router(evidence_router, prefix="/api")
    app.include_router(audit_router)
    app.include_router(signals_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(governance_router)
    app.include_router(capabilities_router, prefix="/api")
    app.include_router(uploads_router, prefix="/api")
    app.include_router(voice_router, prefix="/api")
    app.include_router(scheduler_router, prefix="/api")
    app.include_router(review_router, prefix="/api")
    app.include_router(workflow_router, prefix="/api")
    app.include_router(limbs_router, prefix="/api")

    secret = os.environ.get("MEOWAI_SECRET", "dev-secret-change-in-production")
    app.add_middleware(AuthMiddleware, secret=secret)

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
