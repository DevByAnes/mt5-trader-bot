export type RealtimeType = 'ea_state'|'position'|'signal'|'risk_mode'|'log'|'command_ack'|'config_ack'|'heartbeat';
export type RealtimeEvent = { type: RealtimeType; seq: number; server_time_utc: string; payload: unknown };
export type ConnectionState = { status: 'connecting'|'online'|'offline'; attempt: number; lastEventUtc?: string; gap: boolean };

export function connectRealtime(onEvent: (event: RealtimeEvent) => void, onState: (state: ConnectionState) => void): () => void {
  let socket: WebSocket | undefined; let timer: number | undefined; let stopped = false; let attempt = 0; let lastSeq: number | undefined;
  const connect = () => {
    if (stopped) return; attempt += 1; onState({ status: 'connecting', attempt, gap: false });
    const url = import.meta.env.VITE_WS_URL ?? 'ws://127.0.0.1:8765/ws'; socket = new WebSocket(url);
    socket.onopen = () => { attempt = 0; lastSeq = undefined; onState({ status: 'online', attempt: 0, gap: false }); socket?.send(JSON.stringify({ type: 'snapshot_request' })); };
    socket.onmessage = ({ data }) => { const event = JSON.parse(String(data)) as RealtimeEvent; const gap = lastSeq !== undefined && event.seq !== lastSeq + 1; lastSeq = event.seq; onState({ status: 'online', attempt: 0, lastEventUtc: event.server_time_utc, gap }); onEvent(event); if (gap) socket?.send(JSON.stringify({ type: 'snapshot_request' })); };
    socket.onclose = () => { if (!stopped) { onState({ status: 'offline', attempt, gap: false }); timer = window.setTimeout(connect, Math.min(30_000, 1_000 * 2 ** Math.min(attempt, 5)) + Math.random() * 500); } };
    socket.onerror = () => socket?.close();
  };
  connect(); return () => { stopped = true; if (timer) clearTimeout(timer); socket?.close(); };
}
