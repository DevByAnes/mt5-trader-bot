import { useUiStore } from './store';
export const unavailable = 'Unavailable';
export function numberLocale() { const s = useUiStore.getState(); return `${s.locale === 'fa' ? 'fa-IR' : 'en-US'}-u-nu-${s.digits}`; }
export function numberValue(value: number | null | undefined, locale = numberLocale(), options?: Intl.NumberFormatOptions): string { return value == null || !Number.isFinite(value) ? unavailable : new Intl.NumberFormat(locale, options).format(value); }
export function dateValue(value: string | null | undefined, locale = numberLocale()): string { return !value || !Number.isFinite(Date.parse(value)) ? unavailable : new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value)); }
export function ageLabel(value: string | null | undefined): string { if (!value || !Number.isFinite(Date.parse(value)))
    return unavailable; return `${numberValue(Math.max(0, Math.round((Date.now() - Date.parse(value)) / 1000)))}s`; }
export function countdown(value: string | null | undefined): string { if (!value || !Number.isFinite(Date.parse(value)))
    return unavailable; const s = Math.max(0, Math.floor((Date.parse(value) - Date.now()) / 1000)); return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60].map(n => numberValue(n, undefined, { minimumIntegerDigits: 2, useGrouping: false })).join(':'); }
