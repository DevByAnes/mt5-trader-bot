import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const phase = process.argv[2] ?? 'after';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await mkdir(`docs/screenshots/${phase}`, { recursive: true });
for (const scenario of ['normal', 'python-offline', 'stale']) {
  for (const route of ['overview', 'settings', 'positions', 'chart', 'risk', 'journal', 'validation', 'logs', 'audit']) {
    await page.goto(`http://127.0.0.1:1420/${route}?scenario=${scenario}`);
    await page.waitForTimeout(scenario === 'normal' ? 1300 : 2500);
    if (phase === 'before' && scenario === 'python-offline') {
      await page.context().setOffline(true);
      await page.reload().catch(() => {});
    }
    await page.screenshot({ path: `docs/screenshots/${phase}/${route}-${scenario}.png`, fullPage: true });
    await page.context().setOffline(false);
  }
}
await browser.close();
