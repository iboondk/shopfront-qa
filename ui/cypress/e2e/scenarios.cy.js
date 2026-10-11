/// <reference types="cypress" />

// Same three scenarios as ui/playwright/tests/scenarios.spec.ts (scenario IDs in docs/design-notes.md).

describe('storefront scenarios', () => {
  it('catalog.lists-products', () => {
    cy.visit('/');
    cy.get('[data-testid=product-card]').should('have.length', 8);
    cy.get('[data-testid=product-card]')
      .first()
      .find('[data-testid=product-link]')
      .should('have.text', 'Classic Tee');
  });

  it('product.shows-detail', () => {
    cy.visit('/');
    cy.contains('a', 'Classic Tee').click();
    cy.location('pathname').should('match', /\/products\/classic-tee$/);
    cy.get('[data-testid=product-title]').should('have.text', 'Classic Tee');
    cy.get('[data-testid=product-price]').should('have.text', '$25.00');
  });

  it('cart.add-item', () => {
    cy.visit('/products/classic-tee');
    cy.get('[data-testid=add-to-cart]').click();
    cy.location('pathname').should('match', /\/cart$/);
    cy.get('[data-testid=cart-count]').should('have.text', '1');
  });
});
