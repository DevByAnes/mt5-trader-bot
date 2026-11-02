export type SettingsPhase = 'CLEAN' | 'DIRTY' | 'VALIDATING' | 'REVIEWING_DIFF' | 'CONFIRMING_LOOSEN' | 'SUBMITTING' | 'AWAITING_ACK' | 'APPLIED' | 'REJECTED' | 'TIMEOUT';
export type SettingsEvent = {
    type: 'EDIT';
} | {
    type: 'VALIDATE';
} | {
    type: 'VALIDATED';
    hasLooser: boolean;
} | {
    type: 'CONFIRM';
} | {
    type: 'SUBMIT';
} | {
    type: 'SENT';
} | {
    type: 'FAIL';
} | {
    type: 'ACK';
    status: 'APPLIED' | 'REJECTED';
} | {
    type: 'TIMEOUT';
} | {
    type: 'RESET';
};
export function settingsReducer(state: SettingsPhase, event: SettingsEvent): SettingsPhase {
    if (event.type === 'RESET' && !['SUBMITTING', 'AWAITING_ACK'].includes(state))
        return 'CLEAN';
    if (event.type === 'EDIT' && !['VALIDATING', 'SUBMITTING', 'AWAITING_ACK', 'TIMEOUT'].includes(state))
        return 'DIRTY';
    if (event.type === 'FAIL' && ['VALIDATING', 'SUBMITTING'].includes(state))
        return 'DIRTY';
    if (state === 'DIRTY' && event.type === 'VALIDATE')
        return 'VALIDATING';
    if (state === 'VALIDATING' && event.type === 'VALIDATED')
        return event.hasLooser ? 'CONFIRMING_LOOSEN' : 'REVIEWING_DIFF';
    if (state === 'CONFIRMING_LOOSEN' && event.type === 'CONFIRM')
        return 'REVIEWING_DIFF';
    if (state === 'REVIEWING_DIFF' && event.type === 'SUBMIT')
        return 'SUBMITTING';
    if (state === 'SUBMITTING' && event.type === 'SENT')
        return 'AWAITING_ACK';
    if (['AWAITING_ACK', 'SUBMITTING', 'TIMEOUT'].includes(state) && event.type === 'ACK')
        return event.status;
    if (['SUBMITTING', 'AWAITING_ACK'].includes(state) && event.type === 'TIMEOUT')
        return 'TIMEOUT';
    return state;
}
export function direction(oldValue: unknown, newValue: unknown, riskDirection: string): 'TIGHTER' | 'LOOSER' | 'NEUTRAL' { if (oldValue === newValue || typeof oldValue !== 'number' || typeof newValue !== 'number' || !['HIGHER_IS_LOOSER', 'LOWER_IS_LOOSER'].includes(riskDirection))
    return 'NEUTRAL'; return (riskDirection === 'HIGHER_IS_LOOSER' ? newValue > oldValue : newValue < oldValue) ? 'LOOSER' : 'TIGHTER'; }
