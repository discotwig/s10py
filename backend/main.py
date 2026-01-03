"""Minimal FastAPI app with a WebSocket that streams a counter.

Args:
- None

Returns:
- None
"""

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Dev-only: allow Svelte dev server to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    i = 0
    while True:
        await ws.send_json({"count": i})
        i += 1
        await asyncio.sleep(0.5)
