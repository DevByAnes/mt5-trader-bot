import type { components } from './generated';

export type ApiError = components['schemas']['Error'];
export type Envelope<T> = { data: T; error: ApiError | null; server_time_utc: string; api_version: string };
export type Status = components['schemas']['Status'];
export type EaState = components['schemas']['EaState'];
export type Position = { id:string;side:'BUY'|'SELL';entry:number;sl:number;tp:number;lot:number;r:number;status:string;risk_free:boolean;time_exit_utc?:string|null };
export type Signal = { id:string;time_utc:string;decision:'BUY'|'SELL'|'WAIT'|'NO_SIGNAL';reasons:string[];price?:number|null };
export type DiffItem = { key:string;old_value:unknown;new_value:unknown;apply:'HOT'|'COLD';risk_level:'LOW'|'MEDIUM'|'HIGH';direction:'TIGHTER'|'LOOSER'|'NEUTRAL' };
export type Ack = components['schemas']['Ack'];

const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8765/api/v1';
let sessionToken: string | undefined;

export function setSessionToken(value: string): void { sessionToken = value; }

export class ApiClientError extends Error {
  constructor(public readonly status: number, public readonly detail: ApiError | null) { super(detail?.message ?? `HTTP ${status}`); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Accept', 'application/json');
  if (init?.body) headers.set('Content-Type', 'application/json');
  if (sessionToken) headers.set('Authorization', `Bearer ${sessionToken}`);
  const response = await fetch(`${base}${path}`, { ...init, headers });
  const envelope = await response.json() as Envelope<T>;
  if (!response.ok || envelope.error) throw new ApiClientError(response.status, envelope.error);
  return envelope.data;
}

export const api = {
  status: () => request<Status>('/status'),
  eaState: () => request<EaState>('/ea/state'),
  positions: () => request<Position[]>('/positions'),
  signals: () => request<{ items: Signal[]; next_cursor: string | null }>('/signals'),
  chart: () => request<{ candles: {time:number;open:number;high:number;low:number;close:number}[]; overlays: Record<string, unknown>[] }>('/chart'),
  risk: () => request<Record<string, unknown>>('/risk/daily'),
  settings: () => request<{ version: number; values: SettingsValues; pending_next_day?: boolean }>('/settings'),
  validateSettings: (values: SettingsValues) => request<{ base_version: number; diff: DiffItem[] }>('/settings/validate', { method: 'POST', body: JSON.stringify(values) }),
  applySettings: (baseVersion: number, values: SettingsValues, idempotencyKey = crypto.randomUUID()) => request<Ack>('/settings/apply', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ base_version: baseVersion, values }) }),
  command: (command: Command, positionId?: string, idempotencyKey = crypto.randomUUID()) => request<Ack>(`/commands/${command}`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ position_id: positionId }) }),
  journal: () => request<Record<string, unknown>[]>('/journal'), validation: () => request<Record<string, unknown>[]>('/validation'),
  logs: () => request<Record<string, unknown>[]>('/logs'), audit: () => request<Record<string, unknown>[]>('/audit'),
};

export type Command = 'kill-switch' | 'risk-free-all' | 'risk-free-position' | 'close-position';
export type SettingsValues = { executionMode: 'DEMO'|'FORWARD'|'LIVE'; riskPerTrade: number; dailyLossLimit: number; maxSpread: number; allowRemoteConfig: boolean; allowRealAccount: boolean };
