"""Switch Local Server — Lightweight, standards-compliant Switch protocol server.

Implements the official Agent Switch protocol wire format:
  * Health:           GET  /health
  * Ops discovery:    GET  /agents/{id}/ops
  * Ops call:         POST /agents/{id}/ops/{operation}   (X-Switch-Connection-Id)
  * Post message:     POST /agents/{id}/message           {room_id, content}
  * Events (SSE):     GET  /agents/{id}/events            text/event-stream
  * Room human chat:  POST /rooms/{room_id}/messages      {sender, content}
  * Room history:     GET  /rooms/{room_id}/messages
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [SwitchServer] %(message)s")
logger = logging.getLogger("switch_local_server")

app = FastAPI(title="Switch Local Protocol Server", version="1.0.0")

# In-memory storage for rooms, messages, connections, and event queues
ROOMS: dict[str, dict[str, Any]] = {
    "room-clearance-001": {
        "id": "room-clearance-001",
        "name": "SceneSteward — Footage Clearance",
        "visibility": "private",
        "created_at": datetime.now(UTC).isoformat(),
        "members": ["Elena Producer", "Olivia Director", "Marcus Legal", "SceneSteward Agent", "Google Antigravity"],
    }
}
MESSAGES: list[dict[str, Any]] = []
EVENT_QUEUES: dict[str, asyncio.Queue] = {}
KNOWN_AGENTS: dict[str, dict[str, Any]] = {
    "scenesteward-agent-01": {
        "id": "scenesteward-agent-01",
        "name": "SceneSteward Clearance Agent",
        "registered_at": datetime.now(UTC).isoformat(),
    },
    "google-antigravity-01": {
        "id": "google-antigravity-01",
        "name": "Google Antigravity",
        "registered_at": datetime.now(UTC).isoformat(),
    },
}


class MessageIn(BaseModel):
    room_id: str
    content: str


class HumanMessageIn(BaseModel):
    sender: str
    content: str


class CreateRoomIn(BaseModel):
    name: str
    visibility: str = "private"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "switch-local-gateway", "version": "1.0.0"}


@app.post("/agents/register-known")
def register_known(payload: dict[str, Any], authorization: str | None = Header(None)) -> dict[str, Any]:
    agent_id = payload.get("agent_id") or f"agent-{uuid.uuid4().hex[:8]}"
    KNOWN_AGENTS[agent_id] = {
        "id": agent_id,
        "name": payload.get("name") or "Agent",
        "registered_at": datetime.now(UTC).isoformat(),
    }
    logger.info("Agent registered: %s", agent_id)
    return {"status": "ok", "agent_id": agent_id, "api_key": f"switch-key-{agent_id}"}


@app.get("/agents/{agent_id}/ops")
def get_agent_ops(agent_id: str, authorization: str | None = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Bearer token required")
    logger.info("Agent ops discovery requested for: %s", agent_id)
    return {
        "agent_id": agent_id,
        "operations": ["create_room", "invite_member", "archive_room", "post_message"],
    }


@app.post("/agents/{agent_id}/ops/create_room")
def create_room_op(
    agent_id: str,
    payload: CreateRoomIn,
    x_switch_connection_id: str | None = Header(None, alias="X-Switch-Connection-Id"),
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not x_switch_connection_id:
        raise HTTPException(status_code=400, detail="Missing X-Switch-Connection-Id header")

    room_id = f"switch-room-{uuid.uuid4().hex[:8]}"
    room = {
        "id": room_id,
        "name": payload.name,
        "visibility": payload.visibility,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": agent_id,
        "members": [agent_id],
    }
    ROOMS[room_id] = room
    logger.info("Room created via Switch op: id=%s name='%s'", room_id, payload.name)
    return {"result": {"room_id": room_id, "id": room_id, "name": payload.name}}


@app.post("/agents/{agent_id}/message")
def post_agent_message(
    agent_id: str,
    payload: MessageIn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    event_id = str(uuid.uuid4())
    agent_info = KNOWN_AGENTS.get(agent_id, {})
    agent_name = agent_info.get("name") or ("Google Antigravity" if "antigravity" in agent_id else "SceneSteward Agent")
    msg = {
        "id": event_id,
        "room_id": payload.room_id,
        "sender": agent_name,
        "sender_type": "agent",
        "agent_id": agent_id,
        "content": payload.content,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    MESSAGES.append(msg)
    logger.info("Agent message posted in room %s by '%s': %s", payload.room_id, agent_name, payload.content[:60])
    return {"ok": True, "event_id": event_id}


@app.get("/agents/{agent_id}/events")
async def agent_events_sse(
    request: Request,
    agent_id: str,
    connection_id: str = Query(...),
    start_from: str = Query("head"),
    authorization: str | None = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info("Agent SSE connected: agent_id=%s connection_id=%s", agent_id, connection_id)
    queue: asyncio.Queue = asyncio.Queue()
    EVENT_QUEUES[connection_id] = queue

    # Initial connection frame
    initial_frame = {
        "type": "connection_state",
        "connection_id": connection_id,
        "status": "connected",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    await queue.put(initial_frame)

    async def event_generator():
        seq = 1
        try:
            while True:
                if await request.is_disconnected():
                    logger.info("Agent SSE client disconnected: %s", connection_id)
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    if "sequence" not in event and event.get("type") not in {"connection_state", "keepalive"}:
                        event["sequence"] = seq
                        seq += 1
                    data_str = json.dumps(event)
                    yield f"data: {data_str}\n\n"
                except TimeoutError:
                    # Keep-alive heartbeat frame
                    yield f": heartbeat {datetime.now(UTC).isoformat()}\n\n"
        finally:
            EVENT_QUEUES.pop(connection_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -- Human Interaction & Room Observation Endpoints --

@app.post("/rooms/{room_id}/messages")
async def post_human_message(room_id: str, payload: HumanMessageIn) -> dict[str, Any]:
    if room_id not in ROOMS:
        ROOMS[room_id] = {
            "id": room_id,
            "name": f"Room {room_id}",
            "visibility": "private",
            "created_at": datetime.now(UTC).isoformat(),
            "members": [payload.sender],
        }

    event_id = str(uuid.uuid4())
    msg = {
        "id": event_id,
        "room_id": room_id,
        "sender": payload.sender,
        "sender_type": "human",
        "content": payload.content,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    MESSAGES.append(msg)
    logger.info("Human message in room %s from '%s': %s", room_id, payload.sender, payload.content[:60])

    # Fan out as a Switch event to all connected agent queues
    event_payload = {
        "type": "message",
        "event_id": event_id,
        "data": {
            "room_id": room_id,
            "sender": payload.sender,
            "body": payload.content,
            "content": payload.content,
        },
    }
    for cid, q in list(EVENT_QUEUES.items()):
        await q.put(event_payload)

    return {"status": "posted", "event_id": event_id, "room_id": room_id}


@app.get("/rooms/{room_id}/messages")
def get_room_messages(room_id: str) -> dict[str, Any]:
    room_msgs = [m for m in MESSAGES if m["room_id"] == room_id]
    return {
        "room_id": room_id,
        "count": len(room_msgs),
        "messages": room_msgs,
    }


@app.get("/rooms")
def list_rooms() -> dict[str, Any]:
    return {"rooms": list(ROOMS.values())}


if __name__ == "__main__":
    import os
    import sys
    # Security guard: never allow demo gateway to execute in production mode
    if os.getenv("APP_ENV") == "production":
        logger.error("FATAL: switch_local_server is a local development/demo gateway and is blocked in production")
        sys.exit(1)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="info")

