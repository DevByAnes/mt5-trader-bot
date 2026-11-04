import { copy } from './shared/copy';
import { useEffect, useState } from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { skipToken, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Sun, Moon, Menu } from 'lucide-react';
import { KillSwitch } from './features/killswitch/KillSwitch';
import { useUiStore } from './shared/store';
import { connectRealtime, type ConnectionState } from './shared/api/realtime';
import { api } from './shared/api/client';
import { applyRealtimeEvent } from './shared/api/cache';
import { ageLabel, numberValue, numberLocale } from './shared/format';
import { Overview } from './features/overview/Overview';
import { Positions } from './features/positions/Positions';
import { ChartSignals } from './features/chart/ChartSignals';
import { GenericPage } from './features/generic/GenericPage';
import { SettingsPage } from './features/settings/SettingsPage';
import { scenarios, getScenario } from './mocks/scenarios';
const nav = ['overview', 'settings', 'positions', 'chart', 'risk', 'journal', 'validation', 'logs', 'audit'] as const;
export function App() {
    const { t, i18n } = useTranslation();
    const qc = useQueryClient();
    const ui = useUiStore();
    const source = useQuery<{mode:'fixture'|'file'|'unknown'}>({queryKey:['transport-metadata'], queryFn:skipToken, initialData:{mode:'unknown'}});
    const setBackendOnline = ui.setBackendOnline;
    const [conn, setConn] = useState<ConnectionState>({ status: 'connecting', attempt: 0, gap: false });
    const [open, setOpen] = useState(false);
    const [now, setNow] = useState(new Date());
    const status = useQuery({ queryKey: ['status'], queryFn: api.status });
    const ea = useQuery({ queryKey: ['ea-state'], queryFn: api.eaState });
    useEffect(() => { const timer = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(timer); }, []);
    useEffect(() => connectRealtime(e => applyRealtimeEvent(qc, e), s => { setConn(s); setBackendOnline(s.status === 'online'); }, () => { void qc.invalidateQueries(); }), [qc, setBackendOnline]);
    useEffect(() => { document.documentElement.dir = ui.locale === 'fa' ? 'rtl' : 'ltr'; document.documentElement.lang = ui.locale; document.documentElement.dataset.theme = ui.theme; void i18n.changeLanguage(ui.locale); }, [ui.theme, ui.locale, i18n]);
    const clock = (zone?: string) => new Intl.DateTimeFormat(numberLocale(), { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: zone }).format(now);
    return <div className="app"><header><button className="icon mobile" onClick={() => setOpen(!open)} aria-label={copy("Open navigation")}><Menu /></button><div className="brand-mark">{copy("AU")}</div><div className="brand"><strong>{t('app')}</strong><small>{copy("XAUUSD · Execution oversight")}</small></div><span className="execution-mode">{ea.data?.mode ?? t('unavailable')}</span><KillSwitch /><div className="header-actions"><label className="sr-only" htmlFor="language">{copy("Language")}</label><select id="language" value={ui.locale} onChange={e => ui.setLocale(e.target.value as 'en' | 'fa')}><option value="en">{copy("EN")}</option><option value="fa">فارسی</option></select><label className="sr-only" htmlFor="digits">{copy("Digits")}</label><select id="digits" value={ui.digits} onChange={e => ui.setDigits(e.target.value as 'latn' | 'arabext')}><option value="latn">123</option><option value="arabext">۱۲۳</option></select><button className="icon" onClick={ui.toggleTheme} aria-label={copy("Toggle theme")}>{ui.theme === 'dark' ? <Sun /> : <Moon />}</button></div></header>
 <div className="health-strip" aria-label={copy("Connection health")}>{(['backend', 'ea', 'mt5'] as const).map(k => { const n = status.data?.[k]; const age = n?.heartbeat_utc ? now.getTime() - Date.parse(n.heartbeat_utc) : Infinity; const state = conn.status === 'offline' ? 'offline' : !n ? 'unavailable' : n.state === 'offline' ? 'offline' : age > 6000 ? 'stale' : n.state; return <span className={'health-node ' + state} key={k}><b>{state === 'healthy' ? '✓' : state === 'stale' ? '◷' : '×'} {k === 'backend' ? 'Python' : k.toUpperCase()}</b><span>{state} · {ageLabel(n?.heartbeat_utc)} · {numberValue(n?.latency_ms)} {copy("ms")}</span></span>; })}<span className="clocks" dir="ltr">{copy("UTC")}{clock('UTC')} {copy("· Local")}{clock('Asia/Tehran')} {copy("(Tehran) · Broker UTC")}{status.data?.broker_offset_minutes == null ? 'Unavailable' : numberValue(status.data.broker_offset_minutes / 60)}{copy("h")}</span></div>
 {source.data?.mode==='fixture'&&<div className="transport-banner" data-testid="server-fixture-label">{ui.locale==='fa'?'بک‌اند در حالت شبیه‌سازی است · داده و تأییدها واقعی نیستند':'Backend fixture mode · simulated data and acknowledgements'}</div>}
 {conn.status !== 'online' && <div role="status" className="transport-banner">{conn.status === 'offline' ? t('offline') : conn.status === 'stale' ? 'Stale telemetry · commands disabled' : `Connecting · retry ${numberValue(conn.attempt)}`}</div>}{conn.gap && <div className="transport-banner">{copy("Sequence gap · refreshing authoritative snapshots")}</div>}
 <div className="body"><aside className={open ? 'open' : ''}><div className="nav-label">{copy("Workspace")}</div>{nav.filter(key => key !== 'validation' || source.data?.mode === 'fixture').map((key, i) => <NavLink key={key} to={`/${key}${location.search}`} onClick={() => setOpen(false)}><span className="nav-index">{numberValue(i + 1, undefined, { minimumIntegerDigits: 2 })}</span><span>{t(`nav.${key}`)}</span></NavLink>)}<div className="sidebar-note"><b>{t('policy')}</b><p>{t('warning')}</p></div></aside><main><Routes><Route path="/overview" element={<Overview />}/><Route path="/positions" element={<Positions />}/><Route path="/chart" element={<ChartSignals />}/><Route path="/settings" element={<SettingsPage />}/>{(['risk', 'journal', 'validation', 'logs', 'audit'] as const).map(kind => <Route path={'/' + kind} key={kind} element={<GenericPage kind={kind}/>}/>)}<Route path="*" element={<Navigate to={'/overview' + location.search} replace/>}/></Routes></main></div>
 {import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS !== 'false' && <footer className="dev-bar"><b>{copy("SIMULATED DATA · development")}</b><label>{copy("Scenario")}<select aria-label={copy("Mock scenario")} value={getScenario()} onChange={e => { const url = new URL(location.href); url.searchParams.set('scenario', e.target.value); location.assign(url.href); }}>{scenarios.map(s => <option key={s}>{s}</option>)}</select></label><span>{copy("API v1.0.0 ·")}{conn.status} {conn.attempt > 0 && `retry ${conn.attempt}`}</span></footer>}</div>;
}
