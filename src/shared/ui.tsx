import { copy } from './copy';
import type { ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Clock3, WifiOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { numberValue } from './format';
export function Card({ title, children, className = '' }: {
    title?: string;
    children: ReactNode;
    className?: string;
}) { return <section className={`card ${className}`}>{title && <div className="card-title">{title}</div>}{children}</section>; }
export function Badge({ kind = 'neutral', children }: {
    kind?: 'good' | 'bad' | 'warn' | 'neutral';
    children: ReactNode;
}) { return <span className={`badge ${kind}`}>{kind === 'good' ? <CheckCircle2 /> : kind === 'bad' ? <WifiOff /> : kind === 'warn' ? <AlertTriangle /> : <Clock3 />}{children}</span>; }
export function Metric({ label, value, sub }: {
    label: string;
    value: string;
    sub?: string;
}) { return <Card className="metric-card"><span>{label}</span><strong className="metric" dir="ltr">{value}</strong>{sub && <small>{sub}</small>}</Card>; }
export function PageState({ loading, error, empty, children }: {
    loading: boolean;
    error?: Error | null;
    empty?: boolean;
    children: ReactNode;
}) { const { t } = useTranslation(); if (loading)
    return <div role="status" className="state">{t('loading')}</div>; if (error)
    return <div role="alert" className="state error">{copy("Unavailable ·")}{error.message}<p>{copy("Check the Python bridge. No current values are available.")}</p></div>; if (empty)
    return <div className="state">{t('empty')}</div>; return <>{children}</>; }
export function DataTable({ rows }: {
    rows: Record<string, unknown>[];
}) { const { t } = useTranslation(); if (!rows.length)
    return <div className="state">{t('empty')}</div>; const columns = Object.keys(rows[0] ?? {}).filter(c => c !== 'previous_values'); return <div className="table-wrap"><table><thead><tr>{columns.map(c => <th scope="col" key={c}>{copy(c.replaceAll('_', ' '))}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={String(row.id ?? i)}>{columns.map(c => <td key={c}>{row[c] == null ? t('unavailable') : typeof row[c] === 'number' ? numberValue(row[c]) : Array.isArray(row[c]) ? row[c].join(' · ') : String(row[c])}</td>)}</tr>)}</tbody></table></div>; }
