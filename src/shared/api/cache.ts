import type { QueryClient } from '@tanstack/react-query';
import type { RealtimeEvent } from './realtime';

// These events already carry complete resource snapshots. Refetching every query
// for each event creates a request storm (three STATE events every two seconds).
export function applyRealtimeEvent(client: QueryClient, event: RealtimeEvent) {
    const snapshots: Record<string, string> = {
        heartbeat: 'status', ea_state: 'ea-state', position: 'positions', risk_mode: 'risk',
    };
    const key = snapshots[event.type];
    if (key) {
        client.setQueryData([key], event.payload);
        return;
    }
    const changed = event.type === 'signal' ? ['signals']
        : event.type === 'log' ? ['logs']
        : event.type === 'config_ack' ? ['settings', 'audit']
        : ['positions', 'journal', 'audit'];
    for (const resource of changed) void client.invalidateQueries({queryKey: [resource]});
}
