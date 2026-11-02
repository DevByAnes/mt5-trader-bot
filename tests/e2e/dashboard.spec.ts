import { expect, test } from '@playwright/test';
test('persistent emergency controls and explicit simulation label', async ({ page }) => { await page.goto('/journal'); await expect(page.getByRole('button', { name: 'Halt entries' })).toBeEnabled(); await expect(page.getByText('SIMULATED DATA · development')).toBeVisible(); await expect(page.getByLabel('Connection health')).toContainText('Python'); page.on('dialog', d => d.accept()); await page.getByRole('button', { name: 'Halt entries' }).click(); await expect(page.getByText(/Confirmed by EA/)).toBeVisible(); });
test('reviewed values stay frozen until EA ack', async ({ page }) => { await page.goto('/settings'); const input = page.locator('input[name="riskPerTrade"]'); await input.fill('0.4'); await page.getByRole('button', { name: 'Validate and review changes' }).click(); await expect(page.getByText('TIGHTER', { exact: true })).toBeVisible(); await expect(input).toHaveAttribute('readonly', ''); await page.getByRole('button', { name: 'Apply and await acknowledgement' }).click(); await expect(page.getByText(/EA acknowledged/)).toBeVisible(); await expect(page.getByRole('checkbox', { name: /Remote configuration/ })).toBeDisabled(); });
test('loosening needs a second explicit confirmation', async ({ page }) => { await page.goto('/settings'); await page.locator('input[name="maxSpread"]').fill('40'); await page.getByRole('button', { name: 'Validate and review changes' }).click(); await expect(page.getByText('CONFIRMING_LOOSEN', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Confirm risk loosening' })).toBeDisabled(); await page.getByRole('textbox', { name: 'Risk confirmation' }).fill('LOOSEN RISK'); await page.getByRole('button', { name: 'Confirm risk loosening' }).click(); await page.getByRole('button', { name: 'Apply and await acknowledgement' }).click(); await expect(page.getByText(/EA acknowledged/)).toBeVisible(); });
test('rollback follows validation and acknowledgement', async ({ page }) => { await page.goto('/settings'); await page.getByRole('button', { name: 'Review rollback' }).click(); await expect(page.locator('input[name="maxSpread"]')).toHaveValue('30'); await page.getByRole('button', { name: 'Validate and review changes' }).click(); await page.getByRole('button', { name: 'Apply and await acknowledgement' }).click(); await expect(page.getByText(/EA acknowledged/)).toBeVisible(); });
for (const scenario of ['ack-timeout', 'ack-rejected', 'version-conflict'])
    test('honest settings outcome: ' + scenario, async ({ page }) => { await page.goto('/settings?scenario=' + scenario); await page.locator('input[name="maxSpread"]').fill('30'); await page.getByRole('button', { name: 'Validate and review changes' }).click(); await page.getByRole('button', { name: 'Apply and await acknowledgement' }).click(); await expect(page.getByText(scenario === 'ack-timeout' ? 'Outcome unknown. Do not resubmit.' : scenario === 'ack-rejected' ? /Rejected: EA rejected/ : /Settings changed; reload and review/)).toBeVisible(); await expect(page.getByText(/EA acknowledged/)).toHaveCount(0); });
test('offline disables sends and reconnect recovers', async ({ page }) => { await page.goto('/overview?scenario=python-offline'); await expect(page.getByRole('button', { name: 'Halt entries' })).toBeDisabled(); await expect(page.getByText(/Backend offline/)).toBeVisible(); await page.getByRole('combobox', { name: 'Mock scenario' }).selectOption('normal'); await expect(page.getByRole('button', { name: 'Halt entries' })).toBeEnabled(); await expect(page.getByText('Entries permitted')).toBeVisible(); });
test('stale telemetry is labelled and disables sends', async ({ page }) => { await page.goto('/overview?scenario=stale'); await expect(page.getByText('Stale telemetry · commands disabled')).toBeVisible(); await expect(page.getByRole('button', { name: 'Halt entries' })).toBeDisabled(); });
test('RTL, independent digits, theme and keyboard navigation', async ({ page }) => { await page.goto('/overview'); await page.getByLabel('Language', { exact: true }).selectOption('fa'); await expect(page.locator('html')).toHaveAttribute('dir', 'rtl'); await expect(page.getByRole('heading', { name: 'نمای کلی' })).toBeVisible(); await page.locator('#digits').selectOption('arabext'); await expect(page.locator('main')).toContainText('۱۰٬۰۴۲'); await page.getByRole('button', { name: 'تغییر پوسته' }).click(); await expect(page.locator('html')).toHaveAttribute('data-theme', 'light'); await page.locator('#language').selectOption('en'); await expect(page.locator('html')).toHaveAttribute('dir', 'ltr'); await page.keyboard.press('Tab'); await expect(page.locator(':focus')).toHaveCount(1); });
test('sequence gap refreshes snapshots', async ({ page }) => { await page.goto('/overview?scenario=seq-gap'); await expect(page.getByText(/Sequence gap/)).toBeVisible({ timeout: 10000 }); });
test('overview fits the desktop viewport', async ({ page }) => { await page.setViewportSize({ width: 1440, height: 900 }); await page.goto('/overview'); await expect(page.getByText('Entries permitted')).toBeVisible(); expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(900); });
test('mock enforces idempotency, atomic versions and MT5 locks', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.locator('input[name="maxSpread"]')).toBeVisible();
    const result = await page.evaluate(async () => {
        const base = 'http://127.0.0.1:8765/api/v1';
        const get = async (path: string) => (await (await fetch(base + path)).json()).data;
        const settings = await get('/settings');
        const key = crypto.randomUUID();
        const post = async (path: string, body: unknown, id = key) => { const r = await fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': id }, body: JSON.stringify(body) }); return { status: r.status, body: await r.json() }; };
        const locked = await post('/settings/validate', { base_version: settings.version, values: { ...settings.values, allowRealAccount: true } });
        const body = { base_version: settings.version, values: { ...settings.values, maxSpread: 30 } };
        const first = await post('/settings/apply', body);
        const repeat = await post('/settings/apply', body);
        const mismatch = await post('/settings/apply', { ...body, values: { ...body.values, maxSpread: 31 } });
        const concurrent = await post('/settings/apply', body, crypto.randomUUID());
        const byKey = await get('/requests/' + key);
        return { locked: locked.body.error.code, first: first.body.data, repeat: repeat.body.data, mismatch: mismatch.body.error.code, concurrent: concurrent.body.error.code, byKey };
    });
    expect(result.locked).toBe('MT5_ONLY');
    expect(result.first.status).toBe('PENDING');
    expect(result.first.request_id).toBe(result.repeat.request_id);
    expect(result.byKey.request_id).toBe(result.first.request_id);
    expect(result.mismatch).toBe('IDEMPOTENCY_CONFLICT');
    expect(result.concurrent).toBe('VERSION_CONFLICT');
});
for (const scenario of ['daily-loss', 'daily-profit', 'daily-count', 'no-positions', 'multi-positions', 'wide-spread', 'ea-offline'])
    test('operational scenario ' + scenario, async ({ page }) => { await page.goto('/overview?scenario=' + scenario); if (scenario.startsWith('daily-'))
        await expect(page.getByText('Entries suspended')).toBeVisible(); if (scenario === 'no-positions')
        await expect(page.getByText('No records available')).toBeVisible(); if (scenario === 'multi-positions')
        await expect(page.getByText('XAU-1043')).toBeVisible(); if (scenario === 'wide-spread')
        await expect(page.locator('main')).toContainText('65'); if (scenario === 'ea-offline')
        await expect(page.getByLabel('Connection health')).toContainText('offline'); });
