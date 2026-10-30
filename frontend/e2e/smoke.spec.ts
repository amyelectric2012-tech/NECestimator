import { test, expect } from '@playwright/test';

test('login and open project', async ({ page }) => {
  await page.goto('/');
  await page.fill('input[placeholder="email"]', 'demo@example.com');
  await page.fill('input[placeholder="password"]', 'demo123');
  await page.click('button:has-text("Login")');
  await expect(page.locator('text=Projects')).toBeVisible();
  const openBtn = page.locator('button:has-text("Open")').first();
  if (await openBtn.count()) {
    await openBtn.click();
    await expect(page.locator('text=Run Calculation')).toBeVisible();
  }
});

test('NEC search', async ({ page }) => {
  await page.goto('/');
  await page.fill('input[placeholder="email"]', 'demo@example.com');
  await page.fill('input[placeholder="password"]', 'demo123');
  await page.click('button:has-text("Login")');
  await page.click('text=NEC');
  await page.fill('input[placeholder="Search NEC text..."]', 'grounding');
  await page.click('button:has-text("Search")');
  await expect(page.locator('mark').first()).toBeVisible({ timeout: 10000 });
});
