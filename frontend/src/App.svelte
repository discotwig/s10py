<script>
  import { onMount } from "svelte";
  import { connectWs } from "./ws.js";

  let rpm = 0;

  const maxRpm = 6000;
  const redlineRpm = 5000;

  const shiftRpm = 2500;
  const chillRpm = 3500;

  const startDeg = -130;
  const endDeg = 130;
  const sweep = endDeg - startDeg;

  let rpmSmooth = 0;
  let wobble = 0;

  // Glitch burst controls
  let glitch = false;
  let glitchJitter = 0; // px
  let glitchScan = 0; // px offset for scanline band

  $: pct = Math.max(0, Math.min(1, rpmSmooth / maxRpm));
  $: needleDeg = startDeg + pct * sweep;
  $: needleDegSvg = needleDeg + 90 + wobble;

  $: shiftOn = rpm >= shiftRpm && rpm < chillRpm;
  $: chillOn = rpm >= chillRpm;

  function polar(cx, cy, r, deg) {
    const a = (deg * Math.PI) / 180;
    return { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
  }

  function arcPath(cx, cy, r, a0, a1) {
    const p0 = polar(cx, cy, r, a0);
    const p1 = polar(cx, cy, r, a1);
    const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
    return `M ${p0.x} ${p0.y} A ${r} ${r} 0 ${large} 1 ${p1.x} ${p1.y}`;
  }

  // ticks: minor 250, major 1000
  const tickStep = 250;
  const tickCount = maxRpm / tickStep;
  const ticks = Array.from({ length: tickCount + 1 }, (_, i) => {
    const v = i * tickStep;
    const deg = startDeg + (v / maxRpm) * sweep;
    return { v, deg, major: v % 1000 === 0 };
  });

  // slightly imperfect labels
  const labelKs = [0, 1, 2, 3, 4, 5, 6];
  const labelOffsets = {
    0: { dx: -2, dy: 2 },
    1: { dx: 2, dy: -1 },
    2: { dx: 1, dy: 2 },
    3: { dx: 2, dy: 1 },
    4: { dx: 0, dy: 2 },
    5: { dx: -1, dy: 1 },
    6: { dx: -3, dy: 2 },
  };
  const labels = labelKs.map((k) => {
    const v = k * 1000;
    const deg = startDeg + (v / maxRpm) * sweep;
    const p = polar(100, 100, 59, deg);
    const o = labelOffsets[k] ?? { dx: 0, dy: 0 };
    return { k, x: p.x + o.dx, y: p.y + o.dy };
  });

  // segmented redline overlay
  const redStartDeg = startDeg + (redlineRpm / maxRpm) * sweep;
  const redSegs = [];
  const segSize = 10;
  const gap = 4;
  for (let a = redStartDeg; a < endDeg - 0.5; a += segSize + gap) {
    redSegs.push(arcPath(100, 100, 82, a, Math.min(endDeg, a + segSize)));
  }

  function triggerGlitchBurst() {
    glitch = true;

    // jitter + scan band position
    glitchJitter = Math.round((Math.random() * 2 - 1) * 6); // -6..+6 px
    glitchScan = Math.round(Math.random() * 260); // band vertical offset

    // a few micro-jitters during the burst to make it obvious
    const start = performance.now();
    const jitterTimer = setInterval(() => {
      const t = performance.now() - start;
      glitchJitter = Math.round((Math.random() * 2 - 1) * (6 - (t / 60) * 3));
    }, 18);

    setTimeout(() => {
      clearInterval(jitterTimer);
      glitch = false;
      glitchJitter = 0;
    }, 140);
  }

  onMount(() => {
    connectWs((msg) => {
      if (typeof msg.rpm === "number") rpm = msg.rpm;
    });

    const alpha = 0.18;
    const smoothTimer = setInterval(() => {
      rpmSmooth = rpmSmooth + (rpm - rpmSmooth) * alpha;
      wobble = Math.sin(performance.now() / 120) * (0.18 + pct * 0.28);
    }, 16);

    // rare, but very visible glitch burst (every ~9–16s)
    const glitchTimer = setInterval(
      () => {
        triggerGlitchBurst();
      },
      9000 + Math.floor(Math.random() * 7000),
    );

    return () => {
      clearInterval(smoothTimer);
      clearInterval(glitchTimer);
    };
  });
</script>

<div class="frame">
  <div class="hudScale">
    <!-- Bulbous CRT mask -->
    <div
      class="crtShell"
      style={`--j:${glitchJitter}px; --scan:${glitchScan}px`}
      class:glitch
    >
      <div class="scanlines"></div>
      <div class="crtVignette"></div>
      <div class="crtBulge"></div>
      <div class="crtGlass"></div>

      <!-- Content -->
      <div class="hud">
        <div class="top">
          <div class="title">Chevy S10 // 1999</div>
          <div class="right">2.4L 5-SPEED</div>
        </div>

        <div class="center">
          <div class="gaugeShell">
            <div class="bracket left" aria-hidden="true"></div>

            <div class="gauge">
              <svg viewBox="0 0 200 200" class="svg" aria-label="RPM Gauge">
                <circle cx="100" cy="100" r="84" class="ring" />

                {#each redSegs as d}
                  <path {d} class="redlineSeg" />
                {/each}

                {#each ticks as t}
                  {@const inner = t.major ? 66 : 72}
                  {@const p1 = polar(100, 100, inner, t.deg)}
                  {@const p2 = polar(100, 100, 82, t.deg)}
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    class={t.major ? "tick major" : "tick"}
                  />
                {/each}

                {#each labels as l}
                  <text
                    x={l.x}
                    y={l.y}
                    text-anchor="middle"
                    dominant-baseline="middle"
                    class="tlabel"
                  >
                    {l.k}
                  </text>
                {/each}

                <text x="100" y="124" text-anchor="middle" class="rpmLabel"
                  >RPM</text
                >
                <text x="100" y="154" text-anchor="middle" class="rpmValue"
                  >{Math.round(rpmSmooth)}</text
                >

                <g
                  transform={`rotate(${needleDegSvg} 100 100)`}
                  class="needleGroup"
                >
                  <path
                    d="M 98.8 103
                       L 101.2 103
                       L 102.4 34
                       L 100 26
                       L 97.6 34 Z"
                    class="needle"
                  />
                </g>

                <circle cx="100" cy="100" r="7" class="hub" />
              </svg>
            </div>

            <div class="bracket right" aria-hidden="true"></div>
          </div>

          <div class="shiftWrap">
            <div class="shiftLabel">SHIFT</div>
            <div class="shiftBar">
              <div class="seg seg1" class:on={shiftOn || chillOn}></div>
              <div class="seg seg2" class:on={chillOn}></div>
            </div>
            <div class="shiftNums">{shiftRpm} / {chillRpm}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  @import url("https://fonts.googleapis.com/css2?family=VT323&display=swap");

  :global(html, body) {
    height: 100%;
    margin: 0;
    background: #050705;
  }

  .frame {
    height: 100vh;
    display: grid;
    place-items: center;
  }

  /* Keep 800x480 design and scale */
  .hudScale {
    width: 800px;
    height: 480px;
    transform: scale(min(calc(100vw / 800), calc(100vh / 480)));
    transform-origin: center;
  }

  /* CRT shell (bulbous mask) */
  .crtShell {
    width: 800px;
    height: 480px;

    position: relative;
    overflow: hidden;

    /* "bulbous" curved corners + slight inset */
    border-radius: 20px;
    background: #060806;
    /* border: 1px solid rgba(122, 255, 150, 0.2); */

    /* inner lip */
    box-shadow:
      inset 0 0 0 2px rgba(0, 0, 0, 0.35),
      inset 0 0 45px rgba(0, 0, 0, 0.55),
      0 18px 60px rgba(0, 0, 0, 0.55);
  }

  /* Glitch effect: whole content jitters + scan band */
  .crtShell.glitch .hud {
    transform: translateX(var(--j)) translateY(calc(var(--j) * -0.35));
  }

  .crtShell.glitch .crtGlass {
    opacity: 0.55;
  }

  /* scanlines */
  .scanlines {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      to bottom,
      rgba(0, 0, 0, 0),
      rgba(0, 0, 0, 0) 2px,
      rgba(0, 0, 0, 0.16) 3px
    );
    opacity: 0.42;
    mix-blend-mode: multiply;
  }

  /* vignette + edge falloff like a CRT */
  .crtVignette {
    position: absolute;
    inset: -40px;
    pointer-events: none;
    background: radial-gradient(
        circle at 50% 45%,
        rgba(122, 255, 150, 0.08),
        transparent 55%
      ),
      radial-gradient(
        circle at 50% 50%,
        transparent 45%,
        rgba(0, 0, 0, 0.65) 78%
      );
    opacity: 0.85;
  }

  /* bulge distortion (fake, but sells it): highlights + darker edges */
  .crtBulge {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(
      1200px 700px at 50% 40%,
      rgba(255, 255, 255, 0.06),
      transparent 45%
    );
    opacity: 0.35;
  }

  /* glass + scan band for glitch */
  .crtGlass {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(
        to bottom,
        transparent,
        rgba(255, 255, 255, 0.04),
        transparent
      ),
      linear-gradient(
        to bottom,
        rgba(0, 0, 0, 0) calc(var(--scan) * 1px),
        rgba(122, 255, 150, 0.12) calc(var(--scan) * 1px + 10px),
        rgba(0, 0, 0, 0) calc(var(--scan) * 1px + 26px)
      );
    opacity: 0.18;
    mix-blend-mode: screen;
    transition: opacity 120ms linear;
  }

  /* HUD content */
  .hud {
    position: relative;
    width: 800px;
    height: 480px;
    padding: 16px 28px;

    color: rgba(122, 255, 150, 0.92);
    font-family: "VT323", ui-monospace, monospace;
    letter-spacing: 0.2px;
    text-transform: uppercase;

    background: radial-gradient(
        900px 520px at 30% 25%,
        rgba(122, 255, 150, 0.1),
        transparent 62%
      ),
      radial-gradient(
        700px 420px at 75% 70%,
        rgba(122, 255, 150, 0.07),
        transparent 60%
      ),
      #060806;

    transition: transform 40ms linear;
  }

  .top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-right: 66px;
    border-bottom: 1px solid rgba(122, 255, 150, 0.18);
  }

  .title {
    font-size: 20px;
    font-weight: 500;
    opacity: 0.95;
    padding-left: 20px;
  }

  .right {
    font-size: 16px;
    opacity: 0.7;
    padding-right: 20px;
  }

  .center {
    height: calc(100% - 44px);
    display: grid;
    place-items: center;
    gap: 14px;
    padding-top: 10px;
  }

  /* Gauge + brackets */
  .gaugeShell {
    position: relative;
    display: grid;
    place-items: center;
  }

  .bracket {
    position: absolute;
    top: 50%;
    width: 64px;
    height: 220px;
    transform: translateY(-50%);
    opacity: 0.55;
    filter: drop-shadow(0 0 10px rgba(122, 255, 150, 0.08));
  }

  .bracket::before,
  .bracket::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: rgba(122, 255, 150, 0.22);
  }

  .bracket::before {
    top: 0;
  }
  .bracket::after {
    bottom: 0;
  }

  .bracket.left {
    left: -86px;
    border-left: 2px solid rgba(122, 255, 150, 0.22);
  }

  .bracket.right {
    right: -86px;
    border-right: 2px solid rgba(122, 255, 150, 0.22);
  }

  .bracket.left::before {
    width: 70%;
  }
  .bracket.left::after {
    width: 55%;
  }

  .bracket.right::before {
    width: 55%;
    margin-left: auto;
  }
  .bracket.right::after {
    width: 70%;
    margin-left: auto;
  }

  .gauge {
    width: 360px;
    height: 360px;
    display: grid;
    place-items: center;
    transform: translateY(4px) translateX(3px) rotate(-0.8deg);
    filter: drop-shadow(0 0 18px rgba(122, 255, 150, 0.1));
  }

  .svg {
    width: 340px;
    height: 340px;
  }

  .ring {
    fill: none;
    stroke: rgba(122, 255, 150, 0.22);
    stroke-width: 2;
  }

  .tick {
    stroke: rgba(122, 255, 150, 0.22);
    stroke-width: 2;
  }

  .tick.major {
    stroke: rgba(122, 255, 150, 0.42);
    stroke-width: 3;
  }

  .tlabel {
    fill: rgba(122, 255, 150, 0.62);
    font-size: 14px;
    opacity: 0.85;
  }

  .redlineSeg {
    fill: none;
    stroke: rgba(122, 255, 150, 0.55);
    stroke-width: 6;
    stroke-linecap: round;
    opacity: 0.45;
    filter: drop-shadow(0 0 10px rgba(122, 255, 150, 0.12));
  }

  .rpmLabel {
    fill: rgba(122, 255, 150, 0.55);
    font-size: 16px;
    letter-spacing: 1px;
  }

  .rpmValue {
    fill: rgba(122, 255, 150, 0.95);
    font-size: 34px;
    filter: drop-shadow(0 0 10px rgba(122, 255, 150, 0.1));
  }

  .needleGroup {
    transition: transform 70ms linear;
  }

  .needle {
    fill: rgba(122, 255, 150, 0.82);
    filter: drop-shadow(0 0 10px rgba(122, 255, 150, 0.14));
  }

  .hub {
    fill: rgba(122, 255, 150, 0.55);
    filter: drop-shadow(0 0 10px rgba(122, 255, 150, 0.12));
  }

  /* Shift bar (Casio-ish shadow) */
  .shiftWrap {
    width: 560px;
    display: grid;
    grid-template-columns: 70px 1fr 140px;
    gap: 10px;
    align-items: center;
    padding-bottom: 36px;
  }

  .shiftLabel {
    font-size: 16px;
    opacity: 0.65;
  }

  .shiftNums {
    font-size: 16px;
    opacity: 0.55;
    text-align: right;
  }

  .shiftBar {
    height: 14px;
    border: 1px solid rgba(122, 255, 150, 0.18);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    padding: 4px;

    /* subtle “inset” to feel like a device */
    box-shadow:
      inset 0 2px 0 rgba(0, 0, 0, 0.35),
      inset 0 -2px 0 rgba(122, 255, 150, 0.06);
  }

  .seg {
    border: 1px solid rgba(122, 255, 150, 0.14);
    background: rgba(122, 255, 150, 0.05);
    box-shadow:
      inset 0 2px 0 rgba(0, 0, 0, 0.25),
      inset 0 -2px 0 rgba(122, 255, 150, 0.06);
  }

  .seg.on {
    background: rgba(122, 255, 150, 0.3);
    box-shadow:
      inset 0 2px 0 rgba(0, 0, 0, 0.25),
      0 0 16px rgba(122, 255, 150, 0.1);
  }

  .seg2.on {
    background: rgba(122, 255, 150, 0.48);
    box-shadow:
      inset 0 2px 0 rgba(0, 0, 0, 0.25),
      0 0 22px rgba(122, 255, 150, 0.14);
  }
</style>
