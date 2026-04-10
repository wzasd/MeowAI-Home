"""WebSocket endpoint for streaming agent responses."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.collaboration.a2a_controller import A2AController
from src.collaboration.intent_parser import parse_intent
from src.thread.models import Message
from src.web.stream import ConnectionManager
from src.workflow.executor import DAGExecutor
from src.workflow.templates import WorkflowTemplateFactory

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    app = websocket.app
    tm = app.state.thread_manager
    agent_router = app.state.agent_router

    manager.add(thread_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "send_message":
                await _handle_send_message(
                    websocket, thread_id, data, tm, agent_router, app
                )
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(thread_id, websocket)


async def _handle_send_message(websocket, thread_id, data, tm, agent_router, app):
    content = data.get("content", "").strip()
    if not content:
        await websocket.send_json({"type": "error", "message": "Empty message"})
        return

    thread = await tm.get(thread_id)
    if not thread:
        await websocket.send_json({"type": "error", "message": "Thread not found"})
        return

    if "@" not in content:
        content = f"@{thread.current_cat_id} {content}"

    agents = agent_router.route_message(content)
    intent = parse_intent(content, len(agents))

    # Cancel any active invocations for this thread
    tracker = getattr(app.state, "invocation_tracker", None)
    if tracker:
        tracker.cancel_all(thread_id)

    # Persist user message
    user_msg = Message(role="user", content=intent.clean_message)
    thread.add_message("user", intent.clean_message)
    await tm.add_message(thread.id, user_msg)

    await websocket.send_json({
        "type": "message_sent",
        "message": {"role": "user", "content": intent.clean_message, "cat_id": None},
    })

    await websocket.send_json({
        "type": "intent_mode",
        "mode": intent.workflow or intent.intent,
        "cats": [a["breed_id"] for a in agents],
    })

    try:
        session_chain = getattr(app.state, "session_chain", None)

        dag_executor = None
        template_factory = None
        if intent.workflow:
            agent_registry = getattr(app.state, "agent_registry", None)
            if agent_registry:
                dag_executor = DAGExecutor(
                    agent_registry=agent_registry,
                    session_chain=session_chain,
                    tracker=tracker,
                )
                template_factory = WorkflowTemplateFactory()

        memory_service = getattr(app.state, "memory_service", None)

        controller = A2AController(
            agents,
            session_chain=session_chain,
            dag_executor=dag_executor,
            template_factory=template_factory,
            memory_service=memory_service,
        )

        if intent.workflow:
            await websocket.send_json({
                "type": "workflow_start",
                "workflow": intent.workflow,
                "cats": [a["breed_id"] for a in agents],
            })

        workflow_cat_ids = []
        async for response in controller.execute(intent, intent.clean_message, thread):
            if response.thinking:
                await websocket.send_json({
                    "type": "thinking",
                    "cat_id": response.cat_id,
                    "cat_name": response.cat_name,
                    "content": response.thinking,
                })

            await websocket.send_json({
                "type": "cat_response",
                "cat_id": response.cat_id,
                "cat_name": response.cat_name,
                "content": response.content,
                "target_cats": response.targetCats,
            })

            if intent.workflow:
                workflow_cat_ids.append(response.cat_id)

            assistant_msg = Message(
                role="assistant",
                content=response.content,
                cat_id=response.cat_id,
                thinking=response.thinking,
            )
            thread.add_message("assistant", response.content, cat_id=response.cat_id)
            await tm.add_message(thread.id, assistant_msg)

        await tm.update_thread(thread)

        # Auto-record workflow pattern to procedural memory (with dedup)
        if intent.workflow and memory_service and workflow_cat_ids:
            from src.evolution.process_evolution import ProcessEvolution
            pe = ProcessEvolution(memory_service.procedural)
            success = len(workflow_cat_ids) == len(agents)
            pe.store_or_update(
                name=intent.workflow,
                category="workflow",
                steps=workflow_cat_ids,
                trigger_conditions=[intent.clean_message[:100]],
                outcomes={
                    "total_nodes": len(agents),
                    "success": len(workflow_cat_ids),
                    "failed": max(0, len(agents) - len(workflow_cat_ids)),
                },
                success=success,
            )

        if intent.workflow:
            await websocket.send_json({"type": "workflow_done"})
        else:
            await websocket.send_json({"type": "done"})

    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
