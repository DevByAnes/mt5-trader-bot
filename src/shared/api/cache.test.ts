import {describe, expect, it, vi} from 'vitest';
import {QueryClient} from '@tanstack/react-query';
import {applyRealtimeEvent} from './cache';

describe('FILE snapshot cache', () => {
    it('does not trigger HTTP refetches for a minute of STATE events', () => {
        const client = new QueryClient();
        const invalidate = vi.spyOn(client, 'invalidateQueries');
        for (let i = 0; i < 30; i++) {
            for (const type of ['ea_state', 'position', 'risk_mode', 'heartbeat'] as const)
                applyRealtimeEvent(client, {type, payload: {observed: i}, seq: i + 1, server_time_utc: new Date().toISOString()});
        }
        expect(invalidate).not.toHaveBeenCalled();
        expect(client.getQueryData(['ea-state'])).toEqual({observed: 29});
        expect(client.getQueryData(['risk'])).toEqual({observed: 29});
        client.clear();
    });
});
