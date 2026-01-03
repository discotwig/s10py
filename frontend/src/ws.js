export function connectWs(onData) {
  const ws = new WebSocket("ws://localhost:8000/ws");

  ws.onmessage = (evt) => {
    try {
      onData(JSON.parse(evt.data));
    } catch {
      // ignore
    }
  };

  ws.onclose = () => {
    // simple auto-reconnect
    setTimeout(() => connectWs(onData), 500);
  };

  return ws;
}
