import { useState } from 'react';
import { skipToken, useQuery } from '@tanstack/react-query';
import { api } from '../../shared/api/client';
import { Card, PageState, DataTable } from '../../shared/ui';
import { numberValue } from '../../shared/format';
import { useUiStore } from '../../shared/store';
import type { TransportMetadata } from '../../shared/query';

export function ForwardTest() {
    const fa = useUiStore(s => s.locale === 'fa');
    const source = useQuery<TransportMetadata>({ queryKey: ['transport-metadata'], queryFn: skipToken });
    const report = useQuery({ queryKey: ['forward-test'], queryFn: api.forwardTest, refetchInterval: 30000, enabled: source.data?.mode === 'file' });
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    async function download() {
        setBusy(true); setError('');
        try {
            const value = await api.exportForwardTest();
            const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
            const link = document.createElement('a'); link.href = url;
            link.download = `aurum-forward-${new Date().toISOString().slice(0, 10)}.json`;
            link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch { setError(fa ? 'دریافت گزارش ناموفق بود؛ دوباره تلاش کنید.' : 'Report download failed. Please retry.'); }
        finally { setBusy(false); }
    }
    const r = report.data;
    if (source.data?.mode !== 'file') return null;
    return <Card title={fa ? 'تست یک‌هفته‌ای · ثبت واقعی' : 'One-week forward test · observed data'}>
        <PageState loading={report.isLoading} error={report.error}>
            <p>{fa ? 'ثبت خودکار با دریافت دادهٔ معتبر EA آغاز می‌شود و پس از راه‌اندازی مجدد ادامه دارد. زمان‌های قطع اتصال هم در گزارش مشخص‌اند.' : 'Recording starts with authenticated EA data and survives restarts. Observation gaps are included in the report.'}</p>
            <div className="risk-amounts">
                <span>{fa ? 'بازهٔ مشاهده (ساعت)' : 'Observed span (hours)'}<b>{numberValue(r?.observed_span_hours, undefined, { maximumFractionDigits: 1 })} / 168</b></span>
                <span>{fa ? 'تصمیم‌های ثبت‌شده' : 'Recorded decisions'}<b>{numberValue(r?.decisions)}</b></span>
                <span>{fa ? 'رکوردهای Deal' : 'Deal records'}<b>{numberValue(r?.deals)}</b></span>
                <span>{fa ? 'افت سرمایهٔ نمونه‌برداری‌شده' : 'Sampled equity drawdown'}<b>{numberValue(r?.sampled_max_drawdown_percent, undefined, { maximumFractionDigits: 2 })}%</b></span>
            </div>
            <div className="row"><span>{fa ? 'شروع ثبت / پایان برنامه‌ریزی‌شده' : 'Recording started / target end'}</span><span dir="ltr">{r?.started_utc ?? '—'} / {r?.target_end_utc ?? '—'}</span></div>
            <div className="row"><span>{fa ? 'آخرین نمونه / شکاف‌های بیش از ۳ دقیقه' : 'Latest sample / gaps over 3 minutes'}</span><span>{r?.last_sample_utc ?? '—'} / {numberValue(r?.sample_gaps_over_3_minutes)}</span></div>
            <DataTable rows={r?.reason_counts ?? []}/>
            <p>{fa ? 'افت سرمایه مربوط به کل حساب و نمونه‌های دقیقه‌ای است. تعداد تصمیم و Deal، تعداد معاملات یا نرخ برد نیست. این گزارش تأیید سودآوری نیست.' : 'Drawdown uses whole-account minute samples. Decision and deal counts are not trade counts or win rates. This report does not validate profitability.'}</p>
            <button disabled={busy || !r?.samples} onClick={() => { void download(); }}>{busy ? '…' : fa ? 'دانلود گزارش کامل JSON' : 'Download full JSON report'}</button>
            {error && <p role="alert">{error}</p>}
        </PageState>
    </Card>;
}
