import { copy } from '../../shared/copy';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { api } from '../../shared/api/client';
import { Card, DataTable, PageState } from '../../shared/ui';
import { numberValue, countdown, ageLabel } from '../../shared/format';
export function GenericPage({ kind }: {
    kind: 'risk' | 'journal' | 'validation' | 'logs' | 'audit';
}) {
    const { t } = useTranslation();
    const nav = useNavigate();
    const [filter, setFilter] = useState('');
    const [cursor, setCursor] = useState('');
    const records = useQuery({ queryKey: [kind, cursor], queryFn: async () => kind === 'risk' ? null : cursor ? api.page('/' + kind as '/journal' | '/validation' | '/logs' | '/audit', cursor) : api[kind](), enabled: kind !== 'risk' });
    const risk = useQuery({ queryKey: ['risk'], queryFn: api.risk, enabled: kind === 'risk' });
    const health = useQuery({ queryKey: ['status'], queryFn: api.status, enabled: kind === 'logs' });
    const descriptions = { risk: 'Limits and remaining capacity are calculated by the EA.', journal: 'Execution records supplied by Python. No performance estimates are inferred.', validation: 'Evidence must be reviewed before LIVE. Simulated results are not validation.', logs: 'Bridge / EA / MT5 diagnostics and server logs.', audit: 'Immutable operator history. Rollback creates a new reviewed proposal.' };
    const rows = records.data?.items ?? [];
    const shown = rows.filter(row => JSON.stringify(row).toLowerCase().includes(filter.toLowerCase()));
    return <><div className="page-head"><div><span className="eyebrow">{copy("Operations / records")}</span><h1>{t('nav.' + kind)}</h1><p>{copy(descriptions[kind])}</p></div>{kind === 'audit' && <button onClick={() => nav('/settings' + location.search)}>{t('rollback')}</button>}</div>
 {kind === 'risk' ? <PageState loading={risk.isLoading} error={risk.error}><Card title={copy("Daily protection limits")}><div className="risk-heading"><h2>{risk.data?.state ?? 'Unavailable'}</h2><b>{risk.data?.reason}</b></div><DataTable rows={risk.data ? [{ start_equity: risk.data.start_equity, current_equity: risk.data.current_equity, loss_limit: risk.data.loss_limit_amount, loss_remaining: risk.data.loss_remaining, profit_target: risk.data.profit_target_amount, profit_remaining: risk.data.profit_remaining, trades_remaining: risk.data.trades_remaining }] : []}/><div className="row"><span>{copy("Next trading day")}</span><b>{countdown(risk.data?.next_day_utc)}</b></div></Card></PageState> : <>
 {kind === 'logs' && <Card title={copy("Infrastructure heartbeat ages")}>{(['backend', 'ea', 'mt5'] as const).map(key => <div className="row" key={key}><b>{key === 'backend' ? 'Python' : key.toUpperCase()}</b><span>{health.data?.[key].state ?? 'Unavailable'} · {ageLabel(health.data?.[key].heartbeat_utc)} · {numberValue(health.data?.[key].latency_ms)} {copy("ms")}</span></div>)}</Card>}
 <Card title={t('nav.' + kind)}><label className="filter">{copy("Filter records")}<input value={filter} onChange={e => setFilter(e.target.value)} placeholder={copy("Search current page")}/></label><PageState loading={records.isLoading} error={records.error} empty={!shown.length}><DataTable rows={shown}/></PageState><div className="actions"><button disabled={!cursor} onClick={() => setCursor('')}>{copy("First page")}</button><button disabled={!records.data?.next_cursor} onClick={() => setCursor(records.data!.next_cursor!)}>{copy("Next page")}</button><small>{numberValue(shown.length)} {copy("records on this page")}</small></div></Card></>}</>;
}
