export const unavailable = 'Unavailable';
export function numberValue(value: number|null|undefined, locale='fa-IR', options?: Intl.NumberFormatOptions): string { return value == null ? unavailable : new Intl.NumberFormat(locale, options).format(value); }
export function dateValue(value: string|null|undefined, locale='fa-IR'): string { return value == null ? unavailable : new Intl.DateTimeFormat(locale,{dateStyle:'medium',timeStyle:'medium'}).format(new Date(value)); }
export function ageLabel(value: string|null|undefined): string { if (!value) return unavailable; const seconds=Math.max(0,Math.round((Date.now()-new Date(value).getTime())/1000)); return `${seconds}s ago`; }
