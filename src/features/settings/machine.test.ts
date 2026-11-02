import { describe, expect, it } from 'vitest';
import { direction, settingsReducer } from './machine';
import { validateValues } from './validation';
import fixture from '../../../fixtures/SettingsData.json';
describe('settings safety workflow', () => {
    it('requires a complete review and EA acknowledgement', () => { let s = settingsReducer('CLEAN', { type: 'EDIT' }); s = settingsReducer(s, { type: 'VALIDATE' }); s = settingsReducer(s, { type: 'VALIDATED', hasLooser: true }); expect(s).toBe('CONFIRMING_LOOSEN'); expect(settingsReducer(s, { type: 'SUBMIT' })).toBe(s); s = settingsReducer(s, { type: 'CONFIRM' }); s = settingsReducer(s, { type: 'SUBMIT' }); expect(s).toBe('SUBMITTING'); s = settingsReducer(s, { type: 'SENT' }); expect(s).toBe('AWAITING_ACK'); expect(settingsReducer(s, { type: 'ACK', status: 'APPLIED' })).toBe('APPLIED'); });
    it('cannot fake success or discard an in-flight request', () => { expect(settingsReducer('CLEAN', { type: 'ACK', status: 'APPLIED' })).toBe('CLEAN'); expect(settingsReducer('AWAITING_ACK', { type: 'RESET' })).toBe('AWAITING_ACK'); expect(settingsReducer('AWAITING_ACK', { type: 'EDIT' })).toBe('AWAITING_ACK'); expect(settingsReducer('AWAITING_ACK', { type: 'TIMEOUT' })).toBe('TIMEOUT'); expect(settingsReducer('TIMEOUT', { type: 'EDIT' })).toBe('TIMEOUT'); });
    it('classifies both directions and equality', () => { expect(direction(1, 2, 'HIGHER_IS_LOOSER')).toBe('LOOSER'); expect(direction(2, 1, 'HIGHER_IS_LOOSER')).toBe('TIGHTER'); expect(direction(1, 2, 'LOWER_IS_LOOSER')).toBe('TIGHTER'); expect(direction(2, 1, 'LOWER_IS_LOOSER')).toBe('LOOSER'); expect(direction(1, 1, 'HIGHER_IS_LOOSER')).toBe('NEUTRAL'); expect(direction(1, 2, 'NONE')).toBe('NEUTRAL'); });
    it('validates all values against metadata including step, unknown fields and enums', () => { const v = fixture.data.values; expect(validateValues(v)).toEqual([]); for (const bad of [{ ...v, riskPerTrade: .15 }, { ...v, maxSpread: 101 }, { ...v, executionMode: 'DEMO' }, { ...v, allowRemoteConfig: undefined }, { ...v, secret: 'forbidden' }, { ...v, dailyLossLimit: NaN }])
        expect(validateValues(bad).length).toBeGreaterThan(0); });
});
