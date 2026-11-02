import { copy } from '../../shared/copy';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../../shared/api/client';
import { numberValue } from '../../shared/format';
import { Card, PageState } from '../../shared/ui';
import { CommandButton } from '../killswitch/KillSwitch';
export function PositionTable({ actions = false }: {
    actions?: boolean;
}) { const q = useQuery({ queryKey: ['positions'], queryFn: api.positions }); return <PageState loading={q.isLoading} error={q.error} empty={q.data?.length === 0}><div className="table-wrap"><table><thead><tr>{['Ticket', 'Side', 'Entry', 'SL', 'TP', 'Lot', 'Floating R', 'Protection', ...(actions ? ['Actions'] : [])].map(x => <th key={x}>{copy(x)}</th>)}</tr></thead><tbody>{q.data?.map(p => <tr key={p.id}><td>{p.id}</td><td>{p.side}</td><td>{numberValue(p.entry)}</td><td>{numberValue(p.sl)}</td><td>{numberValue(p.tp)}</td><td>{numberValue(p.lot)}</td><td>{numberValue(p.r)}</td><td>{p.risk_free === null ? 'Unavailable' : p.risk_free ? copy('✓ Risk-free') : copy('△ Risk active')}</td>{actions && <td><div className="actions"><CommandButton command="risk-free-position" label={copy("Protect")} positionId={p.id}/><CommandButton command="close-position" label={copy("Close")} positionId={p.id} critical/></div></td>}</tr>)}</tbody></table></div></PageState>; }
export function Positions() { const { t } = useTranslation(); return <><div className="page-head"><div><span className="eyebrow">{copy("XAUUSD · EA exposure")}</span><h1>{t('nav.positions')}</h1><p>{copy("Volume and floating R are reported by the EA.")}</p></div></div><Card><PositionTable actions/></Card></>; }
