import { test, expect } from '@playwright/test';

test('visual: catalog page @visual', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('catalog.png', { fullPage: true });
});

test('visual: product page @visual', async ({ page }) => {
  await page.goto('/products/classic-tee');
  await expect(page).toHaveScreenshot('product.png');
});
