import { test, expect } from '@playwright/test';

test('catalog.lists-products', async ({ page }) => {
  await page.goto('/');
  const cards = page.getByTestId('product-card');
  await expect(cards).toHaveCount(8);
  await expect(cards.first().getByTestId('product-link')).toHaveText('Classic Tee');
});

test('product.shows-detail', async ({ page }) => {
  await page.goto('/');
  await page
    .getByTestId('product-card')
    .filter({ hasText: 'Classic Tee' })
    .getByTestId('product-link')
    .click();
  await expect(page).toHaveURL(/\/products\/classic-tee$/);
  await expect(page.getByTestId('product-title')).toHaveText('Classic Tee');
  await expect(page.getByTestId('product-price')).toHaveText('$25.00');
});

test('cart.add-item', async ({ page }) => {
  await page.goto('/products/classic-tee');
  await page.getByTestId('add-to-cart').click();
  await expect(page).toHaveURL(/\/cart$/);
  await expect(page.getByTestId('cart-count')).toHaveText('1');
});
