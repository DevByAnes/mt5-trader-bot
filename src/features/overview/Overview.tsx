import { copy } from '../../shared/copy';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../../shared/api/client';
import { countdown, numberValue } from '../../shared/format';
import { Badge, Card, PageState } from '../../shared/ui';
import { PositionTable } from '../positions/Positions';
import { MarketChart } from '../chart/ChartSignals';
function Sparkline({ values }: {
    values: (number | null)[] | undefined;
}) { if (!values?.length || values.some(v => v === null))
    return <span>{copy("Unavailable")}</span>; const nums = values as number[]; const min = Math.min(...nums), max = Math.max(...nums); return <svg className="sparkline" viewBox="0 0 200 32" aria-label={copy("Server telemetry history")}><polyline points={nums.map((v, i) => `${i * 200 / Math.max(1, nums.length - 1)},${28 - (v - min) * 24 / (max - min || 1)}`).join(' ')} fill="none" stroke="currentColor" strokeWidth="1.5"/></svg>; }
export function Overview() {
    const { t } = useTranslation();
    const state = useQuery({ queryKey: ['ea-state'], queryFn: api.eaState });
    const risk = useQuery({ queryKey: ['risk'], queryFn: api.risk });
    const signals = useQuery({ queryKey: ['signals'], queryFn: api.signals });
    const history = useQuery({ queryKey: ['telemetry'], queryFn: api.telemetry });
    const s = state.data, r = risk.data;
    const currency = s?.account_currency ?? (s ? 'USD' : '');
    const f = (v: number | null | undefined) => numberValue(v, undefined, { maximumFractionDigits: 2 });
    const rejections = signals.data?.rejection_counts;
    return <><div className="page-head"><div><span className="eyebrow">{copy("Operations / XAUUSD")}</span><h1>{t('nav.overview')}</h1></div><span className="session">{s?.session ?? t('unavailable')}</span></div><PageState loading={state.isLoading} error={state.error}><div className="overview-grid">
 <Card title={copy("Daily risk · EA authority")} className="risk-primary"><div className="risk-heading"><strong>{r?.state === 'ACTIVE' ? copy('Entries permitted') : r?.state === 'STOPPED' ? copy('Entries suspended') : copy('Unavailable')}</strong><Badge kind={r?.state === 'ACTIVE' ? 'good' : 'warn'}>{r?.state ?? 'Unavailable'}</Badge></div>{r?.reason && <p className="error">{r.reason}</p>}<div className="risk-amounts"><span>{copy("Day-start equity")}<b>${f(r?.start_equity)}</b></span><span>{copy("Trades remaining")}<b>{f(r?.trades_remaining)}</b></span><span>{copy("Next trading day")}<b dir="ltr">{countdown(r?.next_day_utc)}</b></span></div>{[{ label: copy('Daily loss headroom'), value: r?.loss_remaining, total: r?.loss_limit_amount, percent: r?.loss_remaining_percent }, { label: copy('Distance to profit stop'), value: r?.profit_remaining, total: r?.profit_target_amount, percent: r?.profit_remaining_percent }].map(x => <div className="risk-meter" key={x.label}><div><span>{x.label}</span><b>${f(x.value)} / ${f(x.total)}</b></div>{x.percent == null ? <span>{copy("Unavailable")}</span> : <progress value={x.percent} max={100} aria-label={x.label}/>}</div>)}</Card>
 <Card title={copy("Account telemetry")} className="account-panel"><div className="account-value"><span>{copy("Equity")} · {currency}</span><strong>{f(s?.equity)}</strong><Sparkline values={history.data?.equity}/></div><div className="row"><span>{copy("Session P&L")}</span><b className={s?.pnl_today != null && s.pnl_today >= 0 ? 'positive' : 'negative'}>{f(s?.pnl_today)} {currency}</b></div><div className="telemetry"><span>{copy("Spread")}<b>{f(s?.spread)}</b><Sparkline values={history.data?.spread}/></span><span>{copy("ATR · M15")}<b>{f(s?.atr)}</b><Sparkline values={history.data?.atr}/></span></div></Card>
 <Card title={copy("Open positions · reported R")} className="overview-positions"><PositionTable /></Card>
 <Card title={copy("XAUUSD · M15 · EA levels")} className="overview-chart"><MarketChart compact/></Card>
 <Card title={copy("Market context")} className="context-panel">{[{ name: 'H1', trend: s?.trend_h1, strength: s?.h1_strength }, { name: 'H4', trend: s?.trend_h4, strength: s?.h4_strength }].map(x => <div className="context" key={x.name}><div className="row"><b>{x.name}</b><span>{x.trend === 'Bullish' ? '↗' : x.trend === 'Bearish' ? '↘' : '→'} {x.trend ?? 'Unavailable'}</span></div><span>{copy("EA strength ·")}{f(x.strength)} / {numberValue(100)}</span>{x.strength != null && <progress value={x.strength} max={100} aria-label={x.name + ' EA strength'}/>}</div>)}<div className="row"><span>{copy("Trades today")}</span><b>{f(s?.trades_today)}</b></div></Card>
 <Card title={copy("Decision feed / rejection reasons")} className="overview-feed"><PageState loading={signals.isLoading} error={signals.error} empty={!signals.data?.items.length}>{signals.data?.items.map(x => <div className="feed-row" key={x.id}><Badge kind={x.reason_code ? 'warn' : 'neutral'}>{x.decision}</Badge><div><b>{x.reason_code ?? x.reasons.join(' · ')}</b><small>{x.reason_code ? `${f(x.actual)} actual / ${f(x.limit)} limit` : x.id}</small></div><Link to="/journal">{copy("Journal ↗")}</Link></div>)}</PageState><div className="row"><span>{copy("Rejections today · EA counts")}</span><b>{rejections ? numberValue(rejections.reduce((total, r) => total + r.count, 0)) : 'Unavailable'}</b></div><small>{rejections?.map(r => r.code + ' ' + numberValue(r.count)).join(' · ') ?? 'Unavailable'}</small></Card>
 </div></PageState></>;
}
