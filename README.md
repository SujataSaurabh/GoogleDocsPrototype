# CollabDoc — Collaborative Document Prototype

A minimal Python implementation of how Google Docs-style real-time collaboration works.

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Type in terminal
```
uvicorn server:app --reload
```

### 3. Connect clients (open locahost in two or more browsers)
``` 
 http://localhost:8000 
```

Type in either browser and watch the change appear in the other one!

---

## Architecture

```
 ┌──────────┐   edit   ┌────────────────────┐   broadcast   ┌──────────┐
 │ Client A │ ──────▶  │   SERVER           │ ────────────▶ │ Client B │
 │  (Alice) │          │  - holds document  │               │  (Bob)   │
 └──────────┘          │  - tracks clients  │               └──────────┘
                       │  - broadcasts edits│
 ┌──────────┐   edit   │                    │   broadcast   ┌──────────┐
 │ Client C │ ──────▶  │  ws://localhost    │ ────────────▶ │ Client A │
 │  (Carol) │          │       :8765        │               │  (Alice) │
 └──────────┘          └────────────────────┘               └──────────┘
```

## Message Protocol (JSON over WebSocket)

| Direction       | Type           | Fields                        | Meaning                        |
|-----------------|----------------|-------------------------------|--------------------------------|
| Client → Server | `join`         | `username`                    | Register on connect            |
| Client → Server | `edit`         | `content`                     | Send updated document          |
| Server → Client | `init`         | `content`                     | Full doc on connect            |
| Server → Client | `edit`         | `content`, `author`           | Another user's change          |
| Server → Client | `notification` | `text`                        | Join/leave announcement        |
| Server → Client | `user_list`    | `users: [...]`                | Who is currently online        |
| Server → Client | `error`        | `text`                        | Something went wrong           |

## Key Concepts Demonstrated

### 1. WebSockets vs HTTP
- HTTP: client asks → server answers → connection closes
- WebSocket: persistent two-way channel, perfect for real-time sync

### 2. Shared Mutable State
The server holds ONE authoritative `document` dict. All edits go through it.

### 3. Concurrent I/O with asyncio
`asyncio.gather(receive_messages, send_edits)` runs both loops
simultaneously in a single thread — no blocking.

### 4. Broadcast Pattern
When any client edits:
  1. Server applies the change to shared state
  2. Server sends the new content to every OTHER client
  3. The editing client already has the latest version, so it's excluded

## What a Production System Would Add

| Feature                    | How                                          |
|---------------------------|----------------------------------------------|
| **Conflict resolution**    | Operational Transforms (OT) or CRDTs         |
| **Cursor positions**       | Broadcast cursor index along with edits      |
| **Persistence**            | Store document in a database (Postgres, etc.)|
| **Authentication**         | JWT tokens on the join handshake             |
| **Undo history**           | Store a list of operations, not just content |
| **Rich text**              | Send structured JSON (like Quill's Delta)    |
| **Scaling**                | Pub/sub (Redis) so multiple server instances |
|                           | can talk to each other                       |
