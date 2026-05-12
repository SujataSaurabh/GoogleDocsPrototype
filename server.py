"""
Collaborative Document Server
------------------------------
Like Google Docs — multiple clients edit the same document in real time.

How it works:
1. Server holds the single source of truth (the document text)
2. Each client connects via WebSocket
3. When a client sends an edit, the server applies it and broadcasts to ALL clients
4. Every client stays in sync automatically
"""

import asyncio
import json
import websockets

# ── Shared state ─────────────────────────────────────────────────────────────

document = {"content": "Welcome to CollabDoc! Start typing...\n"}
connected_clients: dict[websockets.WebSocketServerProtocol, str] = {}  # socket → username


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_message(msg_type: str, **kwargs) -> str:
    """Build a JSON message to send over the wire."""
    return json.dumps({"type": msg_type, **kwargs})


async def broadcast(message: str, exclude=None):
    """Send a message to every connected client (optionally skip one)."""
    targets = [ws for ws in connected_clients if ws != exclude]
    if targets:
        await asyncio.gather(*[ws.send(message) for ws in targets])


async def broadcast_user_list():
    """Tell everyone who is currently online."""
    users = list(connected_clients.values())
    await broadcast(make_message("user_list", users=users))


# ── Connection handler ────────────────────────────────────────────────────────

async def handle_client(websocket):
    """
    Lifecycle of one client connection:
      CONNECT  → register, send current doc, announce arrival
      MESSAGES → apply edits, broadcast to others
      DISCONNECT → unregister, announce departure
    """
    username = None
    try:
        # ── Handshake: first message must be {"type": "join", "username": "..."} ──
        raw = await websocket.recv()
        data = json.loads(raw)

        if data.get("type") != "join" or not data.get("username"):
            await websocket.send(make_message("error", text="First message must be a join with a username."))
            return

        username = data["username"].strip() or "Anonymous"
        connected_clients[websocket] = username

        print(f"[+] {username} joined  (total: {len(connected_clients)})")

        # Send the current document to the newcomer
        await websocket.send(make_message("init", content=document["content"]))

        # Tell everyone (including the newcomer) about the updated user list
        await broadcast_user_list()

        # Announce the arrival to other clients
        await broadcast(
            make_message("notification", text=f"{username} joined the document"),
            exclude=websocket,
        )

        # ── Main loop: handle edits ───────────────────────────────────────────
        async for raw in websocket:
            data = json.loads(raw)

            if data.get("type") == "edit":
                new_content = data.get("content", "")
                document["content"] = new_content          # apply to shared state
                print(f"[edit] {username}: {len(new_content)} chars")

                # Broadcast the change to everyone else
                await broadcast(
                    make_message("edit", content=new_content, author=username),
                    exclude=websocket,
                )

    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[!] Connection error for {username}: {e}")
    finally:
        if websocket in connected_clients:
            del connected_clients[websocket]
            print(f"[-] {username} left  (total: {len(connected_clients)})")
            await broadcast_user_list()
            await broadcast(make_message("notification", text=f"{username} left the document"))


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    print("CollabDoc server starting on ws://localhost:8765")
    print("Open multiple terminal tabs and run: python client.py <YourName>")
    async with websockets.serve(handle_client, "localhost", 8765):
        await asyncio.Future()   # run forever


if __name__ == "__main__":
    asyncio.run(main())
