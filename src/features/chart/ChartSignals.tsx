import { copy } from '../../shared/copy';
import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CandlestickSeries, ColorType, createChart, type UTCTimestamp } from 'lightweight-charts';
import { useTranslation } from 'react-i18next';
import { api } from '../../shared/api/client';
import { Card, DataTable, PageState } from '../../shared/ui';
import { useUiStore } from '../../shared/store';
export function MarketChart({ compact = false }: {
    compact?: boolean;
}) { const ref = useRef<HTMLDivElement>(null); const data = useQuery({ queryKey: ['chart'], queryFn: api.chart }); const theme = useUiStore(s => s.theme); useEffect(() => { if (!ref.current || !data.data)
    return; const chart = createChart(ref.current, { height: compact ? 190 : 360, layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: theme === 'dark' ? '#aeb8c7' : '#475569' }, grid: { vertLines: { color: theme === 'dark' ? '#28313c' : '#d8dce2' }, horzLines: { color: theme === 'dark' ? '#28313c' : '#d8dce2' } }, timeScale: { timeVisible: true }, rightPriceScale: { borderVisible: false } }); const series = chart.addSeries(CandlestickSeries, { upColor: '#71bba1', downColor: '#db7e83', borderVisible: false, wickUpColor: '#71bba1', wickDownColor: '#db7e83' }); series.setData(data.data.candles.map(c => ({ ...c, time: c.time as UTCTimestamp }))); data.data.overlays.forEach(o => series.createPriceLine({ price: o.price, title: o.label, color: o.label === 'SL' ? '#db7e83' : o.label === 'TP' ? '#71bba1' : '#b9c2cf', lineWidth: 1, axisLabelVisible: true })); chart.timeScale().fitContent(); const resize = new ResizeObserver(() => { if (ref.current)
    chart.applyOptions({ width: ref.current.clientWidth }); }); resize.observe(ref.current); return () => { resize.disconnect(); chart.remove(); }; }, [data.data, compact, theme]); return <PageState loading={data.isLoading} error={data.error} empty={data.data?.candles.length === 0}><div ref={ref} className={compact ? 'chart compact' : 'chart'} aria-label={copy("M15 candles with EA Entry, SL and TP")}/></PageState>; }
export function ChartSignals() { const { t } = useTranslation(); const signals = useQuery({ queryKey: ['signals'], queryFn: api.signals }); return <><div className="page-head"><div><span className="eyebrow">{copy("XAUUSD · M15")}</span><h1>{t('nav.chart')}</h1><p>{copy("EA signal decisions and server-reported price levels.")}</p></div></div><Card title={copy("M15 · Entry / SL / TP")}><MarketChart /></Card><Card title={copy("Decision feed")}><PageState loading={signals.isLoading} error={signals.error} empty={!signals.data?.items.length}><DataTable rows={signals.data?.items ?? []}/></PageState></Card></>; }
