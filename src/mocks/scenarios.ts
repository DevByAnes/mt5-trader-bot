export const scenarios = ['normal', 'ea-offline', 'python-offline', 'stale', 'seq-gap', 'ack-rejected', 'ack-timeout', 'version-conflict', 'daily-loss', 'daily-profit', 'daily-count', 'wide-spread', 'no-positions', 'multi-positions'] as const;
export type Scenario = typeof scenarios[number];
export function getScenario(): Scenario { const value = new URLSearchParams(location.search).get('scenario'); return scenarios.find(s => s === value) ?? 'normal'; }
