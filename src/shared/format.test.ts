import { describe, expect, it, vi } from 'vitest';
import { numberValue, dateValue, ageLabel, countdown, unavailable } from './format';
import { useUiStore } from './store';
describe('safe consistent formatting', () => {
    it('does not invent missing values', () => { for (const v of [null, undefined, NaN, Infinity])
        expect(numberValue(v)).toBe(unavailable); expect(numberValue(0)).toBe('0'); expect(dateValue('bad')).toBe(unavailable); expect(ageLabel('bad')).toBe(unavailable); });
    it('honors explicit digit preference independently of language', () => { useUiStore.setState({ locale: 'en', digits: 'latn' }); expect(numberValue(12)).toBe('12'); useUiStore.setState({ locale: 'fa', digits: 'latn' }); expect(numberValue(12)).toBe('12'); useUiStore.setState({ locale: 'fa', digits: 'arabext' }); expect(numberValue(12)).toBe('۱۲'); useUiStore.setState({ locale: 'en', digits: 'latn' }); });
    it('formats ages and trading-day countdown', () => { vi.useFakeTimers(); vi.setSystemTime(new Date('2026-11-02T10:00:00Z')); expect(ageLabel('2026-11-02T09:59:58Z')).toBe('2s'); expect(countdown('2026-11-02T11:02:03Z')).toBe('01:02:03'); vi.useRealTimers(); });
});
