"""FastAPI app with WebSocket streaming a fake 3-gear pull RPM pattern.

Pattern:
- Idle -> 1st gear to 3000 -> shift drop
- 2nd gear to >4000 -> shift drop
- 3rd gear to 6000 (redline) -> lift -> idle (repeat)
"""

import asyncio
import random
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

latest_rpm = 0


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


async def hold_idle(seconds: float, idle: int = 850):
    global latest_rpm
    steps = int(seconds / 0.05)
    for _ in range(steps):
        latest_rpm = clamp(idle + random.randint(-40, 40), 650, 1100)
        await asyncio.sleep(0.05)


async def ramp_to(target: int, step_lo: int, step_hi: int, redline: int = 6000):
    """Ramp RPM upward toward target."""
    global latest_rpm
    while latest_rpm < target:
        latest_rpm += random.randint(step_lo, step_hi)
        latest_rpm = clamp(latest_rpm, 650, redline)
        await asyncio.sleep(0.05)


async def shift_drop(drop_to: int):
    """Quick RPM drop to emulate clutch + next gear."""
    global latest_rpm
    # fast-ish drop with a tiny wobble
    while latest_rpm > drop_to:
        latest_rpm -= random.randint(220, 360)
        latest_rpm = max(latest_rpm, drop_to)
        await asyncio.sleep(0.03)

    # settle for a beat
    for _ in range(8):
        latest_rpm = clamp(drop_to + random.randint(-60, 60), 650, 6000)
        await asyncio.sleep(0.05)


async def fake_gear_pull():
    """Looping 3-gear pull: 3000 shift, >4000 shift, 6000 redline."""
    global latest_rpm

    idle = 850
    redline = 6000

    # Targets per your ask
    gear1_target = 3000
    gear2_target = random.randint(4100, 4400)  # "above 4000"
    gear3_target = redline

    while True:
        # Idle before pull
        latest_rpm = idle
        await hold_idle(2.5, idle=idle)

        # 1st gear -> 3000
        await ramp_to(gear1_target, 120, 200, redline=redline)
        await asyncio.sleep(0.15)  # tiny hang at shift point
        await shift_drop(drop_to=1800)

        # 2nd gear -> >4000
        await ramp_to(gear2_target, 90, 160, redline=redline)
        await asyncio.sleep(0.12)
        await shift_drop(drop_to=2400)

        # 3rd gear -> redline 6000
        await ramp_to(gear3_target, 70, 140, redline=redline)
        # hit limiter bounce a couple times
        for _ in range(10):
            latest_rpm = redline - random.randint(0, 120)
            await asyncio.sleep(0.04)

        # Lift off / decel back to idle
        while latest_rpm > idle:
            latest_rpm -= random.randint(180, 300)
            latest_rpm = max(latest_rpm, idle)
            await asyncio.sleep(0.05)

        # vary the next run slightly
        gear2_target = random.randint(4100, 4500)


@app.on_event("startup")
async def startup():
    asyncio.create_task(fake_gear_pull())


@app.get("/health")
def health():
    return {"ok": True}


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()

    # Stream RPM at ~20Hz
    while True:
        await ws.send_json({"rpm": latest_rpm})
        await asyncio.sleep(0.05)
