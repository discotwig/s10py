<script>
  import { onMount } from "svelte";
  import { connectWs } from "./ws.js";

  let count = null;

  onMount(() => {
    connectWs((msg) => {
      count = msg.count;
    });
  });
</script>

<main style="font-family: system-ui; padding: 24px;">
  <h1>S10PY</h1>
  <p>WebSocket count: <b>{count ?? "connecting..."}</b></p>
</main>
