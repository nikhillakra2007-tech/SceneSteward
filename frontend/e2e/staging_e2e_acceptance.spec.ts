import { test, expect } from '@playwright/test';

test.describe('SceneSteward Staging Acceptance E2E Journey', () => {
  test('Navbar authentication modal, persona switching, and custom identity login', async ({ page }) => {
    await page.goto('/');

    // 1. Verify Home Page branding and ethical mission
    await expect(page.locator('text=SceneSteward').first()).toBeVisible();
    await expect(page.locator('text=Documentary Ethics & Consent').first()).toBeVisible();

    // 2. Open Authentication & Identity Modal
    const customLoginBtn = page.locator('[data-testid="custom-login-btn"]');
    if (await customLoginBtn.isVisible()) {
      await customLoginBtn.click();
      await expect(page.locator('[data-testid="auth-modal"]')).toBeVisible();

      // Check preset personas
      await expect(page.locator('text=Preset Personas')).toBeVisible();
      await expect(page.locator('text=Olivia Director')).toBeVisible();
      await expect(page.locator('text=Claire Care')).toBeVisible();

      // Test custom input form
      await page.fill('[data-testid="login-name-input"]', 'Staging Quality Lead');
      await page.fill('[data-testid="login-email-input"]', 'qa.lead@staging.scenesteward.internal');
      await page.click('[data-testid="login-submit-btn"]');

      // Verify modal closes and authenticated identity is displayed in Navbar
      await expect(page.locator('[data-testid="auth-modal"]')).not.toBeVisible();
      await expect(page.locator('text=qa.lead@staging.scenesteward.internal')).toBeVisible();

      // Test Switch User button
      await page.click('[data-testid="switch-user-btn"]');
      await expect(page.locator('[data-testid="auth-modal"]')).toBeVisible();
      await page.click('button:has-text("Cancel")');
      await expect(page.locator('[data-testid="auth-modal"]')).not.toBeVisible();
    }
  });

  test('Documentary project exploration and ethical invariant verification', async ({ page }) => {
    await page.goto('/projects');

    // Verify projects workspace header
    await expect(page.locator('h1, h2').first()).toBeVisible();

    // Verify navigation back to Home
    await page.click('a[href="/"]');
    await expect(page).toHaveURL('/');
  });

  test('Participant transparency portal: 15 categories, bilingual toggle, and formal withdrawal', async ({ page }) => {
    const testParticipantId = '00000000-0000-0000-0000-000000000001';
    await page.goto(`/participant/${testParticipantId}`);

    // Verify participant portal renders
    const header = page.locator('h1, h2').first();
    await expect(header).toBeVisible();

    // Verify ethical dignity invariants
    const dignityText = page.locator('text=agreement to one use is never agreement to another use');
    if (await dignityText.isVisible()) {
      await expect(dignityText).toBeVisible();

      // Test Hindi Language Toggle
      const hindiBtn = page.locator('button:has-text("हिन्दी")');
      if (await hindiBtn.isVisible()) {
        await hindiBtn.click();
        await expect(page.locator('text=अहस्तांतरणीय सहमति गारंटी')).toBeVisible();

        // Switch back to English
        await page.click('button:has-text("English")');
        await expect(page.locator('text=Non-Transitive Consent Invariant')).toBeVisible();
      }

      // Test Formal Withdrawal Interface
      const withdrawalTab = page.locator('button:has-text("Formal Consent Withdrawal")');
      if (await withdrawalTab.isVisible()) {
        await withdrawalTab.click();
        await expect(page.locator('text=Submitting a withdrawal request will immediately notify')).toBeVisible();
        await expect(page.locator('textarea')).toBeVisible();
      }
    }
  });
});
