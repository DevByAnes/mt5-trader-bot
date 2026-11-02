import { delay, http, HttpResponse, ws } from 'msw';
import settingsSchema from '../../schema/settings.schema.json';
import type { Ack, Models, SettingsValues } from '../shared/api/client';
import { direction } from '../features/settings/machine';
import { validateValues } from '../features/settings/validation';
import { getScenario } from './scenarios';
import statusFixture from '../../fixtures/Status.json';
import eaFixture from '../../fixtures/EaState.json';
import positionFixture from '../../fixtures/Positions.json';
import signalFixture from '../../fixtures/Signals.json';
import chartFixture from '../../fixtures/Chart.json';
import riskFixture from '../../fixtures/DailyRisk.json';
import telemetryFixture from '../../fixtures/Telemetry.json';
import settingsFixture from '../../fixtures/SettingsData.json';
import journalFixture from '../../fixtures/Journal.json';
import validationFixture from '../../fixtures/Validation.json';
import logFixture from '../../fixtures/Logs.json';
import auditFixture from '../../fixtures/Audit.json';
const now = () => new Date().toISOString();
const envelope = <T>(data: T) => ({ data, error: null, server_time_utc: now(), api_version: '1.0.0' });
let version = 7;
let values = structuredClone(settingsFixture.data.values) as SettingsValues;
const audits = structuredClone(auditFixture.data.items) as Models['AuditRecord'][];
let halted = false;
let protectedAll = false;
const closed = new Set<string>();
const protectedIds = new Set<string>();
const subscribers = new Set<(type: string, payload: unknown) => void>();
const broadcast = (type: string, payload: unknown) => subscribers.forEach(send => send(type, payload));
const requests = new Map<string, Ack>();
const keys = new Map<string, {
    body: string;
    id: string;
}>();
const fail = (code: Models['Error']['code'], message: string, status = 422) => HttpResponse.json({ ...envelope(null), error: { code, message } }, { status });
const clone = <T>(x: T) => structuredClone(x);
function status() { const x = clone(statusFixture.data) as Models['Status']; for (const k of ['backend', 'ea', 'mt5'] as const) {
    x[k].heartbeat_utc = new Date(Date.now() - (getScenario() === 'stale' ? 12000 : 0)).toISOString();
    if (getScenario() === 'stale')
        x[k].state = 'stale';
} if (getScenario() === 'ea-offline')
    x.ea.state = 'offline'; return x; }
function ea() { const x = clone(eaFixture.data) as Models['EaState']; x.mode = values.executionMode; if (halted) {
    x.risk_active = false;
    x.risk_reason = 'OPERATOR_HALT';
} if (getScenario().startsWith('daily-')) {
    x.risk_active = false;
    x.risk_reason = getScenario().toUpperCase();
} if (getScenario() === 'wide-spread')
    x.spread = 65; return x; }
function positions() {
    if (getScenario() === 'no-positions') return [];
    const initial = clone(positionFixture.data);
    const all = getScenario() === 'multi-positions' ? [...initial, { ...initial[0], id: 'XAU-1043', side: 'SELL', r: -.12 }] : initial;
    return all.filter(p => !closed.has(p.id)).map(p => ({ ...p, risk_free: protectedAll || protectedIds.has(p.id) || p.risk_free }));
}
function risk() { const x = clone(riskFixture.data) as Models['DailyRisk']; x.next_day_utc = new Date(new Date().setUTCHours(24, 0, 0, 0)).toISOString(); if (getScenario().startsWith('daily-')) {
    x.state = 'STOPPED';
    x.reason = getScenario().toUpperCase();
    if (getScenario() === 'daily-loss') {
        x.loss_remaining = 0;
        x.loss_remaining_percent = 0;
    }
    if (getScenario() === 'daily-profit') {
        x.profit_remaining = 0;
        x.profit_remaining_percent = 0;
    }
    if (getScenario() === 'daily-count')
        x.trades_remaining = 0;
} return x; }
function diff(draft: SettingsValues): Models['Diff'] { return { base_version: version, values: draft, diff: Object.entries(draft).filter(([k, v]) => values[k as keyof SettingsValues] !== v).map(([key, new_value]) => { const meta = settingsSchema.properties[key as keyof SettingsValues]; return { key, old_value: values[key as keyof SettingsValues], new_value, apply: meta.apply as 'HOT' | 'COLD', risk_level: meta.risk_level as 'HIGH' | 'MEDIUM', direction: direction(values[key as keyof SettingsValues], new_value, meta.risk_direction) }; }) }; }
function validate(draft: SettingsValues) { if (validateValues(draft).length)
    return fail('VALIDATION_ERROR', 'Invalid fields: ' + validateValues(draft).join(', ')); for (const [k, m] of Object.entries(settingsSchema.properties))
    if (m.mt5_only && draft[k as keyof SettingsValues] !== values[k as keyof SettingsValues])
        return fail('MT5_ONLY', k + ' is controlled in MT5', 403); if (draft.executionMode === 'LIVE')
    return fail('LIVE_LOCKED', 'MT5 real account permission missing', 403); return null; }
const bridge = ws.link('ws://127.0.0.1:8765/ws');
const bridgeHandler = bridge.addEventListener('connection', ({ client }) => { if (getScenario() === 'python-offline') {
    client.close(1013, 'Python offline');
    return;
} let seq = 0; const send = (type: string, payload: unknown) => client.send(JSON.stringify({ type, seq: ++seq, server_time_utc: now(), payload })); subscribers.add(send); const tick = () => { if (getScenario() === 'seq-gap' && seq === 2)
    seq++; client.send(JSON.stringify({ type: 'heartbeat', seq: ++seq, server_time_utc: now(), payload: status() })); }; tick(); send('signal', {...signalFixture.data.items[0],time_utc:now()}); const timer = setInterval(tick, 2000); client.addEventListener('close', () => { clearInterval(timer); subscribers.delete(send); }); });
function accept(request: Request, body: unknown, apply?: () => void) { const key = request.headers.get('Idempotency-Key'); if (!key)
    return fail('VALIDATION_ERROR', 'Idempotency-Key required'); const signature = request.url + JSON.stringify(body); const previous = keys.get(key); if (previous)
    return previous.body === signature ? HttpResponse.json(envelope(requests.get(previous.id)), { status: 202 }) : fail('IDEMPOTENCY_CONFLICT', 'Key reused with different payload', 409); if (getScenario() === 'ea-offline')
    return fail('EA_OFFLINE', 'EA disconnected; command not sent', 503); const id = crypto.randomUUID(); const ack: Ack = { request_id: id, status: 'PENDING', reason: null, version: null, ea_ack_utc: null }; requests.set(id, ack); keys.set(key, { body: signature, id }); setTimeout(() => { if (getScenario() === 'ack-timeout') {
    ack.status = 'TIMEOUT';
    ack.reason = 'Outcome unknown';
    return;
} if (getScenario() === 'ack-rejected') {
    ack.status = 'REJECTED';
    ack.reason = 'EA rejected simulated request';
    broadcast(request.url.includes('settings') ? 'config_ack' : 'command_ack', ack);
    return;
} apply?.(); ack.status = 'APPLIED'; ack.version = version; ack.ea_ack_utc = now(); broadcast(request.url.includes('settings') ? 'config_ack' : 'command_ack', ack); broadcast('ea_state', ea()); broadcast('position', positions()); broadcast('risk_mode', risk()); broadcast('log', { id: crypto.randomUUID(), time_utc: now(), level: 'INFO', source: 'mock-EA', message: 'Simulated EA acknowledgement' }); }, 700); return HttpResponse.json(envelope(ack), { status: 202 }); }
const records = { journal: journalFixture.data, validation: validationFixture.data, logs: logFixture.data };
function page<T extends {id:string}>(items:T[],request:Request){
    const query=new URL(request.url).searchParams;const limit=Number(query.get('limit')??50);const cursor=query.get('cursor');
    if(!Number.isInteger(limit)||limit<1||limit>100)return fail('VALIDATION_ERROR','limit must be an integer from 1 to 100');
    let offset=0;
    if(cursor){let id:string;try{id=atob(cursor);}catch{return fail('VALIDATION_ERROR','Invalid cursor');}offset=items.findIndex(x=>x.id===id)+1;if(offset===0)return fail('VALIDATION_ERROR','Expired cursor');}
    const selected=items.slice(offset,offset+limit);return {items:selected,next_cursor:offset+limit<items.length?btoa(selected[selected.length-1]!.id):null};
}
export const handlers = [bridgeHandler,
    http.all('*/api/v1/*', () => getScenario() === 'python-offline' ? HttpResponse.error() : undefined),
    http.get('*/api/v1/status', () => HttpResponse.json(envelope(status()))),
    http.get('*/api/v1/ea/state', () => HttpResponse.json(envelope(ea()))),
    http.get('*/api/v1/positions', () => HttpResponse.json(envelope(positions()))),
    http.get('*/api/v1/signals', ({request}) => {const result=page(signalFixture.data.items.map(x=>({...x,time_utc:now()})),request);return result instanceof Response?result:HttpResponse.json(envelope({...result,rejection_counts:signalFixture.data.rejection_counts}));}),
    http.get('*/api/v1/chart', () => HttpResponse.json(envelope(chartFixture.data))),
    http.get('*/api/v1/telemetry', () => HttpResponse.json(envelope(telemetryFixture.data))),
    http.get('*/api/v1/risk/daily', () => HttpResponse.json(envelope(risk()))),
    http.get('*/api/v1/settings', () => HttpResponse.json(envelope({ version, values, pending_next_day: false }))),
    http.post('*/api/v1/settings/validate', async ({ request }) => { await delay(100); const body = await request.json() as Models['ApplyRequest']; if (body.base_version !== version)
        return fail('VERSION_CONFLICT', 'Settings changed; reload and review', 409); return validate(body.values) ?? HttpResponse.json(envelope(diff(body.values))); }),
    http.post('*/api/v1/settings/apply', async ({ request }) => { const body = await request.json() as Models['ApplyRequest']; if (keys.has(request.headers.get('Idempotency-Key') ?? ''))
        return accept(request, body); if ([...keys.values()].some(k => k.body.includes('/settings/apply') && ['PENDING', 'TIMEOUT'].includes(requests.get(k.id)!.status)) || body.base_version !== version || getScenario() === 'version-conflict')
        return fail('VERSION_CONFLICT', 'Settings changed; reload and review', 409); const error = validate(body.values); if (error)
        return error; return accept(request, body, () => { audits.unshift({ id: crypto.randomUUID(), time_utc: now(), actor: 'mock-operator', action: 'SETTINGS_APPLIED', version: version + 1, result: 'APPLIED', previous_values: clone(values) }); values = body.values; version++; }); }),
    http.post('*/api/v1/commands/:command', async ({ request, params }) => { if (!['kill-switch', 'risk-free-all', 'risk-free-position', 'close-position'].includes(String(params.command)))
        return fail('NOT_FOUND', 'Unknown command', 404); const body = await request.json() as Models['CommandRequest']; if (['risk-free-position', 'close-position'].includes(String(params.command)) && !body.position_id)
        return fail('VALIDATION_ERROR', 'position_id required'); return accept(request, body, () => { if (params.command === 'kill-switch')
        halted = true; if (params.command === 'risk-free-all')
        protectedAll = true; if (params.command === 'risk-free-position' && body.position_id)
        protectedIds.add(body.position_id); if (params.command === 'close-position' && body.position_id)
        closed.add(body.position_id); }); }),
    http.get('*/api/v1/requests/:id', ({ params }) => requests.has(keys.get(String(params.id))?.id ?? String(params.id)) ? HttpResponse.json(envelope(requests.get(keys.get(String(params.id))?.id ?? String(params.id)))) : fail('NOT_FOUND', 'Request not found', 404)),
    http.post('*/api/v1/audit/:id/rollback', ({ params }) => { const row = audits.find(x => x.id === params.id); return row ? HttpResponse.json(envelope(diff(row.previous_values))) : fail('NOT_FOUND', 'Audit record missing', 404); }),
    ...Object.entries(records).map(([path, data]) => http.get('*/api/v1/' + path, ({request}) => {const result=page(data.items as {id:string}[],request);return result instanceof Response?result:HttpResponse.json(envelope(result));})),
    http.get('*/api/v1/audit', ({request}) => {const result=page(audits,request);return result instanceof Response?result:HttpResponse.json(envelope(result));})];
