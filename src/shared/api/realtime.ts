import type { Models } from './client';
export type ConnectionState = {
    status: 'connecting' | 'online' | 'offline' | 'stale';
    attempt: number;
    lastEventUtc?: string;
    gap: boolean;
};
export type RealtimeEvent = {
    type: 'ea_state' | 'position' | 'signal' | 'risk_mode' | 'log' | 'command_ack' | 'config_ack' | 'heartbeat';
    seq: number;
    server_time_utc: string;
    payload: unknown;
};
export function connectRealtime(onEvent: (e: RealtimeEvent) => void, onState: (s: ConnectionState) => void, onSnapshot: () => void): () => void {
    let socket: WebSocket | undefined, timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false, attempt = 0, lastSeq: number | undefined, lastSeen = Date.now(), healthStale = true;
    const connect = () => {
        if (stopped)
            return;
        onState({ status: 'connecting', attempt, gap: false });
        socket = new WebSocket(import.meta.env.VITE_WS_URL ?? 'ws://127.0.0.1:8765/ws');
        socket.onopen = () => { attempt = 0; lastSeq = undefined; lastSeen = Date.now(); onSnapshot(); };
        socket.onmessage = ({ data }) => { try {
            const e = JSON.parse(String(data)) as RealtimeEvent;
            if (!Number.isSafeInteger(e.seq) || e.seq < 1 || !Number.isFinite(Date.parse(e.server_time_utc)) || !['ea_state', 'position', 'signal', 'risk_mode', 'log', 'command_ack', 'config_ack', 'heartbeat'].includes(e.type))
                throw Error('Invalid event');
            if (lastSeq !== undefined && e.seq <= lastSeq)
                return;
            const gap = lastSeq !== undefined && e.seq !== lastSeq + 1;
            lastSeq = e.seq;
            lastSeen = Date.now();
            const health = e.type === 'heartbeat' ? e.payload as Models['Status'] : undefined;
            if (health) healthStale = Object.values(health).some(n => n && typeof n === 'object' && 'state' in n && (n.state === 'stale' || ('heartbeat_utc' in n && typeof n.heartbeat_utc === 'string' && Date.now() - Date.parse(n.heartbeat_utc) > 6000)));
            onState({ status: healthStale ? 'stale' : 'online', attempt: 0, lastEventUtc: e.server_time_utc, gap });
            if (gap)
                onSnapshot();
            onEvent(e);
        }
        catch {
            onSnapshot();
        } };
        socket.onclose = () => { if (stopped)
            return; attempt++; onState({ status: 'offline', attempt, gap: false }); timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** Math.min(attempt - 1, 5)) + Math.random() * 300); };
        socket.onerror = () => socket?.close();
    };
    const watchdog = setInterval(() => { if (socket?.readyState === WebSocket.OPEN && Date.now() - lastSeen > 6000) {
        onState({ status: 'stale', attempt, gap: false });
        if (Date.now() - lastSeen > 15000)
            socket.close();
    } }, 1000);
    connect();
    return () => { stopped = true; clearTimeout(timer); clearInterval(watchdog); socket?.close(); };
}
