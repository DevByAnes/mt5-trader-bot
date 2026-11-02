import { copy } from '../../shared/copy';
import { useMutation } from '@tanstack/react-query';
import { OctagonX, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api, awaitAck, ApiClientError, type Command, type Ack } from '../../shared/api/client';
import { useUiStore } from '../../shared/store';
export function CommandButton({ command, label, positionId, critical = false }: {
    command: Command;
    label: string;
    positionId?: string;
    critical?: boolean;
}) {
    const online = useUiStore(s => s.backendOnline);
    const mutation = useMutation({ mutationFn: async (reconcileId?: string) => { const key = reconcileId ?? crypto.randomUUID(); try {
            return await awaitAck(reconcileId ? await api.ack(key) : await api.command(command, positionId, key));
        }
        catch (e) {
            if (e instanceof ApiClientError && [400, 403, 404, 409, 422, 503].includes(e.status))
                throw e;
            return { request_id: key, status: 'TIMEOUT', reason: String(e), version: null, ea_ack_utc: null } as Ack;
        } } });
    return <div className="command"><button className={critical ? 'critical' : ''} onClick={() => { if (online && confirm(`Confirm: ${label}?`))
        mutation.mutate(undefined); }} disabled={!online || mutation.isPending || mutation.data?.status === 'TIMEOUT'}>{critical ? <OctagonX /> : <ShieldCheck />}{mutation.isPending ? copy('Awaiting EA…') : label}</button>{!online && <small>{copy("Not sent · offline / stale")}</small>}{mutation.data && <small role="status">{mutation.data.status === 'APPLIED' ? copy('Confirmed by EA') : mutation.data.status === 'TIMEOUT' ? copy('Outcome unknown') : mutation.data.status} · {mutation.data.request_id}{mutation.data.status === 'TIMEOUT' && <button disabled={!online} onClick={() => mutation.mutate(mutation.data!.request_id)}>{copy("Reconcile")}</button>}</small>}{mutation.error && <small role="alert" className="error">{copy("Outcome unconfirmed:")}{mutation.error.message}</small>}</div>;
}
export function KillSwitch() { const { t } = useTranslation(); return <div className="kill-switch" aria-label={copy("Emergency controls")}><CommandButton command="kill-switch" label={t('kill')} critical/><CommandButton command="risk-free-all" label={t('riskFree')}/></div>; }
