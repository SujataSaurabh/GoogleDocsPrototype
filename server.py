"""
CollabDoc Web Server
--------------------
FastAPI + WebSockets backend.
- Serves the frontend HTML at GET /
- Handles WebSocket connections at ws://localhost:8000/ws/{username}

Install:
    pip install fastapi uvicorn websockets

Run:
    uvicorn server:app --reload
    then open http://localhost:8000
"""

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

# ── Shared state ──────────────────────────────────────────────────────────────

document = {"content": "Welcome to CollabDoc! Click here and start typing...\n"}
connected: dict[str, WebSocket] = {}   # username → websocket


# ── Helpers ───────────────────────────────────────────────────────────────────

def msg(**kwargs) -> str:
    return json.dumps(kwargs)


async def broadcast(skip: str = None, **kwargs):
    dead = []
    for uname, ws in connected.items():
        if uname == skip:
            continue
        try:
            await ws.send_text(msg(**kwargs))
        except Exception:
            dead.append(uname)
    for u in dead:
        connected.pop(u, None)


async def broadcast_users():
    await broadcast(type="user_list", users=list(connected.keys()))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    html = Path("index.html").read_text()
    return HTMLResponse(html)


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()

    # Handle duplicate usernames
    if username in connected:
        await websocket.send_text(msg(type="error", text=f"Username '{username}' is already taken."))
        await websocket.close()
        return

    connected[username] = websocket
    print(f"[+] {username} joined  (total: {len(connected)})")

    # Send current doc state to newcomer
    await websocket.send_text(msg(type="init", content=document["content"]))

    # Tell everyone about updated user list + arrival
    await broadcast_users()
    await broadcast(skip=username, type="notification", text=f"{username} joined", kind="join")

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "edit":
                document["content"] = data["content"]
                print(f"[edit] {username}: {len(data['content'])} chars")
                await broadcast(skip=username, type="edit", content=data["content"], author=username)

    except WebSocketDisconnect:
        connected.pop(username, None)
        print(f"[-] {username} left  (total: {len(connected)})")
        await broadcast_users()
        await broadcast(skip=username, type="notification", text=f"{username} left", kind="leave")
