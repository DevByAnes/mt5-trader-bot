import type { components, paths } from './generated';
import type { components as SessionComponents } from './session-generated';
import { queryClient, type TransportMetadata } from '../query';
export type Models = components['schemas'];
export type ApiError = Models['Error'];
export type Status = Models['Status'];
export type EaState = Models['EaState'];
export type Position = Models['Position'];
export type Signal = Models['Signal'];
export type DiffItem = Models['DiffItem'];
export type Ack = Models['Ack'];
export type SettingsValues = Models['SettingsDraft'];
export type Command = paths['/commands/{command}']['post']['parameters']['path']['command'];
export interface ForwardReport {
    report_version: number; started_utc: string | null; last_sample_utc: string | null;
    target_end_utc: string | null; observed_span_hours: number; samples: number;
    decisions: number; deals: number; sample_gaps_over_3_minutes: number;
    sampled_max_drawdown_percent: number | null; reason_counts: {code: string; count: number}[];
}
type GetPath = {
    [P in keyof paths]: paths[P] extends {
        get: {
            responses: {
                200: unknown;
            };
        };
    } ? P : never;
}[keyof paths];
type GetData<P extends GetPath> = paths[P] extends {
    get: {
        responses: {
            200: {
                content: {
                    'application/json': {
                        data: infer D;
                    };
                };
            };
        };
    };
} ? D : never;
const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8765/api/v1';
let sessionToken: string | undefined;
let rateLimitedUntil = 0;
export function setSessionToken(value: string) { sessionToken = value; }
export class ApiClientError extends Error {
    constructor(public readonly status: number, public readonly detail: ApiError | null, public readonly retryAfterMs?: number) { super(detail?.message ?? `HTTP ${status}`); }
}
async function request<T>(path: string, init?: RequestInit, apiBase = base): Promise<T> {
    if ((!init?.method || init.method === 'GET') && Date.now() < rateLimitedUntil)
        throw new ApiClientError(503, {code: 'UNAVAILABLE', message: 'Request rate exceeded; reconnecting automatically'}, rateLimitedUntil - Date.now());
    const headers = new Headers(init?.headers);
    headers.set('Accept', 'application/json');
    if (init?.body)
        headers.set('Content-Type', 'application/json');
    if (sessionToken)
        headers.set('Authorization', `Bearer ${sessionToken}`);
    const response = await fetch(apiBase + path, { ...init, headers, signal: AbortSignal.timeout(5000) });
    const mode = response.headers.get('X-Aurum-Mode');
    if (mode === 'fixture' || mode === 'file') queryClient.setQueryData<TransportMetadata>(['transport-metadata'], {mode});
    const body = await response.json();
    if (response.status === 429 || (response.status === 503 && body.error?.message === 'Request rate exceeded')) {
        const seconds = Number(response.headers.get('Retry-After') ?? '60');
        const delay = Number.isFinite(seconds) && seconds > 0 ? Math.min(seconds, 300) * 1000 : 60000;
        rateLimitedUntil = Date.now() + delay;
        throw new ApiClientError(response.status, body.error, delay);
    }
    if (!response.ok || body.error)
        throw new ApiClientError(response.status, body.error);
    if (body.api_version !== '1.0.0' || body.data === undefined)
        throw Error('Unsupported bridge response');
    return body.data as T;
}
const get = <P extends GetPath>(path: P) => request<GetData<P>>(path);
const post = <T>(path: string, body: unknown, key?: string) => request<T>(path, { method: 'POST', body: JSON.stringify(body), ...(key ? { headers: { 'Idempotency-Key': key } } : {}) });
export const api = { status: () => get('/status'), eaState: () => get('/ea/state'), positions: () => get('/positions'), signals: () => get('/signals'), chart: () => get('/chart'), risk: () => get('/risk/daily'), telemetry: () => get('/telemetry'), settings: () => get('/settings'),
    forwardTest: () => request<ForwardReport>('/forward-test', undefined, base.replace(/\/v1\/?$/, '/v2')),
    exportForwardTest: () => request<unknown>('/forward-test/export', undefined, base.replace(/\/v1\/?$/, '/v2')),
    socketTicket: () => request<SessionComponents['schemas']['SocketTicket']>('/session/ws-ticket', { method: 'POST' }, base.replace(/\/v1\/?$/, '/v2')),
    validateSettings: (body: Models['ApplyRequest']) => post<Models['Diff']>('/settings/validate', body),
    applySettings: (base_version: number, values: SettingsValues, key: string = crypto.randomUUID()) => post<Ack>('/settings/apply', { base_version, values }, key),
    command: (command: Command, positionId?: string, key: string = crypto.randomUUID()) => post<Ack>('/commands/' + command, positionId ? { position_id: positionId } : {}, key),
    ack: (id: string) => request<Ack>('/requests/' + encodeURIComponent(id)), rollback: (id: string) => post<Models['Diff']>('/audit/' + encodeURIComponent(id) + '/rollback', {}),
    journal: () => get('/journal'), validation: () => get('/validation'), logs: () => get('/logs'), audit: () => get('/audit'),
    page: <P extends '/journal' | '/validation' | '/logs' | '/audit' | '/signals'>(path: P, cursor: string) => request<GetData<P>>(path + '?cursor=' + encodeURIComponent(cursor)) };
export async function awaitAck(initial: Ack, onPending?: () => void): Promise<Ack> { if (initial.status !== 'PENDING')
    return verified(initial); onPending?.(); const deadline = Date.now() + 10000; while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 300));
    const ack = await api.ack(initial.request_id);
    if (ack.status !== 'PENDING')
        return verified(ack);
} return { ...initial, status: 'TIMEOUT', reason: 'Outcome unknown; reconcile request ID before retrying' }; }
function verified(ack: Ack): Ack { if (ack.status === 'APPLIED' && !ack.ea_ack_utc)
    throw Error('APPLIED has no EA acknowledgement'); return ack; }
