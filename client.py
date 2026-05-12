"""
Collaborative Document Client
------------------------------
Connects to the server, lets you edit the document, and shows
changes made by other users — all in real time.

Usage:
    python client.py Alice
    python client.py Bob      ← open in a second terminal tab
"""

import asyncio
import json
import sys
import websockets

SERVER_URI = "ws://localhost:8765"


def make_message(msg_type: str, **kwargs) -> str:
    return json.dumps({"type": msg_type, **kwargs})


# ── Display helpers ───────────────────────────────────────────────────────────

def clear_line():
    print("\r" + " " * 80 + "\r", end="", flush=True)


def print_doc(content: str, header: str = ""):
    print("\n" + "=" * 60)
    if header:
        print(f"  {header}")
        print("-" * 60)
    print(content)
    print("=" * 60)


# ── Receive loop (runs concurrently with the send loop) ──────────────────────

async def receive_messages(websocket, username: str):
    """
    Listen for server messages in the background.
    Types we handle:
      init         → initial document state on connection
      edit         → another user changed the document
      notification → join/leave announcements
      user_list    → who is currently online
      error        → server-side error
    """
    async for raw in websocket:
        data = json.loads(raw)
        msg_type = data.get("type")

        if msg_type == "init":
            print_doc(data["content"], header="📄 Current Document")

        elif msg_type == "edit":
            author = data.get("author", "someone")
            clear_line()
            print(f"\n✏️  [{author}] made an edit:")
            print_doc(data["content"])
            print("Your edit (or press Enter to skip): ", end="", flush=True)

        elif msg_type == "notification":
            clear_line()
            print(f"\n🔔 {data['text']}")
            print("Your edit (or press Enter to skip): ", end="", flush=True)

        elif msg_type == "user_list":
            users = data.get("users", [])
            clear_line()
            print(f"\n👥 Online: {', '.join(users)}")
            print("Your edit (or press Enter to skip): ", end="", flush=True)

        elif msg_type == "error":
            print(f"\n❌ Server error: {data.get('text')}")


# ── Send loop ─────────────────────────────────────────────────────────────────

async def send_edits(websocket):
    """
    Read lines from stdin (non-blocking via run_in_executor).
    Empty line  → skip (do nothing)
    Any text    → replace document content and send to server
    'quit'      → disconnect

    In a real app you'd send diffs (operational transforms / CRDTs).
    Here we send the full document for simplicity.
    """
    loop = asyncio.get_event_loop()

    print("\nType your edit and press Enter.  Empty line = skip.  'quit' = exit.\n")

    while True:
        # Read input without blocking the asyncio event loop
        line = await loop.run_in_executor(None, sys.stdin.readline)
        line = line.rstrip("\n")

        if line.lower() == "quit":
            print("Goodbye!")
            await websocket.close()
            break

        if line == "":
            continue   # skip empty lines

        # For demo purposes the "full document" is just whatever the user typed.
        # A real system would maintain a local copy and apply the diff.
        await websocket.send(make_message("edit", content=line))
        print(f"✅ Sent your edit ({len(line)} chars)")
        print("Your edit (or press Enter to skip): ", end="", flush=True)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main(username: str):
    print(f"Connecting to {SERVER_URI} as '{username}'…")
    try:
        async with websockets.connect(SERVER_URI) as websocket:
            # Step 1: Join
            await websocket.send(make_message("join", username=username))

            # Step 2: Run receiver and sender concurrently
            await asyncio.gather(
                receive_messages(websocket, username),
                send_edits(websocket),
            )
    except ConnectionRefusedError:
        print(f"❌ Could not connect to {SERVER_URI}")
        print("   Make sure the server is running:  python server.py")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Anonymous"
    asyncio.run(main(name))
