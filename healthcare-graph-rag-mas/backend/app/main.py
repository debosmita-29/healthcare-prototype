from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.api.run_registry import run_registry
from app.core.settings import get_settings
from app.graph.orchestrator import BriefingGraphOrchestrator
from app.models.schemas import BriefingRequest, BriefingResponse, CostPerformanceSummary
from app.observability.audit import audit_sink
from app.observability.phoenix import configure_phoenix

settings = get_settings()
orchestrator = BriefingGraphOrchestrator(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_phoenix(settings)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)
except Exception:
    # Observability should never block API startup in the prototype.
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.post("/api/briefings", response_model=BriefingResponse)
async def create_briefing(request: BriefingRequest) -> BriefingResponse:
    temporary_run_id = f"pending_{uuid.uuid4().hex[:8]}"
    pending = BriefingResponse(
        run_id=temporary_run_id,
        condition=request.condition,
        status="running",
        performance=CostPerformanceSummary(),
    )
    run_registry.create_pending(temporary_run_id, pending)

    async def execute() -> None:
        audit_queue = audit_sink.subscribe(temporary_run_id)

        async def forward_audit_events() -> None:
            while True:
                event = await audit_queue.get()
                await run_registry.publish(temporary_run_id, {"event": "audit", **event})

        forwarder = asyncio.create_task(forward_audit_events())
        await run_registry.publish(
            temporary_run_id,
            {"event": "started", "node": "api", "message": "Graph execution started"},
        )
        try:
            response = await orchestrator.run(
                condition=request.condition,
                audience=request.audience,
                include_companies=request.include_companies,
                include_trials=request.include_trials,
                run_id=temporary_run_id,
            )
            run_registry.set_response(response)
            await run_registry.publish(
                temporary_run_id,
                {"event": "complete", "node": "api", "status": response.status},
            )
        except Exception as exc:
            failed = run_registry.get(temporary_run_id) or pending
            failed.status = "failed"
            failed.audit_events = audit_sink.list(temporary_run_id)
            failed.audit_events.append(
                {"run_id": temporary_run_id, "node": "api", "event_type": "error", "payload": {"message": str(exc)}}
            )
            run_registry.set_response(failed)
            await run_registry.publish(
                temporary_run_id,
                {"event": "complete", "node": "api", "status": "failed", "error": str(exc)},
            )
        finally:
            forwarder.cancel()
            audit_sink.unsubscribe(temporary_run_id, audit_queue)

    asyncio.create_task(execute())
    return pending


@app.get("/api/briefings/{run_id}", response_model=BriefingResponse)
async def get_briefing(run_id: str) -> BriefingResponse:
    response = run_registry.get(run_id)
    if not response:
        raise HTTPException(status_code=404, detail="Run not found")
    return response


@app.get("/api/briefings/{run_id}/events")
async def stream_events(run_id: str) -> StreamingResponse:
    queue = run_registry.queue(run_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event, default=str)}\n\n"
            if event.get("event") == "complete":
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.websocket("/ws/briefings/{run_id}")
async def websocket_events(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    queue = run_registry.queue(run_id)
    if not queue:
        await websocket.send_json({"event": "error", "message": "Run not found"})
        await websocket.close()
        return
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("event") == "complete":
                await websocket.close()
                return
    except WebSocketDisconnect:
        return
