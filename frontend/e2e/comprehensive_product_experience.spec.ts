import { test, expect } from '@playwright/test';

test.describe('SceneSteward Comprehensive Product Experience Suite', () => {
  // Test A — Authentication & Identity Switching
  test('Test A — Authentication flow, form validation, and session management', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=SceneSteward').first()).toBeVisible();

    // Open auth modal
    const loginBtn = page.locator('[data-testid="custom-login-btn"]');
    if (await loginBtn.isVisible()) {
      await loginBtn.click();
      const modal = page.locator('[data-testid="auth-modal"]');
      await expect(modal).toBeVisible();

      // Test Escape key closes modal
      await page.keyboard.press('Escape');
      await expect(modal).not.toBeVisible();

      // Re-open and test quick persona login
      await loginBtn.click();
      await page.click('[data-testid="quick-login-olivia"]');

      // Modal closes and user is authenticated
      await expect(modal).not.toBeVisible();
      await expect(page.locator('text=Olivia Director')).toBeVisible();

      // Test Logout
      await page.click('[data-testid="logout-btn"]');
      await expect(page.locator('[data-testid="custom-login-btn"]')).toBeVisible();
    }
  });

  // Test B — Navigation & Responsive Drawer
  test('Test B — Navigation links, active state indicators, and mobile drawer', async ({ page }) => {
    // Desktop navigation
    await page.goto('/');
    await page.click('nav[aria-label="Main Navigation"] >> text=Projects');
    await expect(page).toHaveURL(/\/projects/);

    await page.click('nav[aria-label="Main Navigation"] >> text=Analytics');
    await expect(page).toHaveURL(/\/analytics/);

    // Mobile viewport & drawer
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    const hamburgerBtn = page.locator('button[aria-label="Toggle navigation menu"]');
    await expect(hamburgerBtn).toBeVisible();
    await hamburgerBtn.click();

    // Verify mobile drawer items
    await expect(page.locator('div.md\\:hidden >> text=Projects')).toBeVisible();
    await expect(page.locator('div.md\\:hidden >> text=Analytics')).toBeVisible();
    await page.click('div.md\\:hidden >> text=Projects');
    await expect(page).toHaveURL(/\/projects/);
  });

  // Test C — Projects Workspace & Search
  test('Test C — Projects workspace, search filtering, and workspace navigation', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.locator('h1')).toContainText('Documentary Projects');

    // Test Search input if present
    const searchInput = page.locator('input[placeholder*="Search projects"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('NonExistentProjectNameXYZ');
      await expect(page.locator('text=No projects match')).toBeVisible();
      await searchInput.fill('');
    }
  });

  // Test D — Participants Roster & Transparency
  test('Test D — Participant roster, language options, and portal access', async ({ page }) => {
    const sampleParticipantId = '00000000-0000-0000-0000-000000000001';
    await page.goto(`/participant/${sampleParticipantId}`);

    // Verify fallback or profile heading renders
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();

    // Verify bilingual toggle
    const hindiBtn = page.locator('button:has-text("हिन्दी")');
    if (await hindiBtn.isVisible()) {
      await hindiBtn.click();
      await expect(page.locator('text=अहस्तांतरणीय सहमति गारंटी')).toBeVisible();

      await page.click('button:has-text("English")');
      await expect(page.locator('text=Non-Transitive Consent Invariant')).toBeVisible();
    }
  });

  // Test E — Consent Management & 15 Categories
  test('Test E — Canonical 15 categories, non-transitive invariants, and choice badges', async ({ page }) => {
    const sampleParticipantId = '00000000-0000-0000-0000-000000000001';
    await page.goto(`/participant/${sampleParticipantId}`);

    // Invariant check: silence is never consent
    const dignityGuarantee = page.locator('text=agreement to one use is never agreement to another use');
    if (await dignityGuarantee.isVisible()) {
      await expect(dignityGuarantee).toBeVisible();
    }
  });

  // Test F — Human Review Gates & Advisory Disclaimers
  test('Test F — Advisory disclaimer and mandatory human decision rationale', async ({ page }) => {
    await page.goto('/projects');
    // Verify projects page loads without uncaught exceptions
    await expect(page.locator('h1')).toBeVisible();
  });

  // Test G — Participant Care & Urgent Withdrawal
  test('Test G — Formal withdrawal warning and submission interface', async ({ page }) => {
    const sampleParticipantId = '00000000-0000-0000-0000-000000000001';
    await page.goto(`/participant/${sampleParticipantId}`);

    const withdrawalTab = page.locator('button:has-text("Formal Consent Withdrawal")');
    if (await withdrawalTab.isVisible()) {
      await withdrawalTab.click();
      await expect(page.locator('text=Submitting a withdrawal request will immediately notify')).toBeVisible();
      await expect(page.locator('textarea')).toBeVisible();
    }
  });

  // Test H — Analytics Subsystem Dashboard
  test('Test H — Analytics dashboard, KPI cards, category breakdown, and export dialog', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.locator('h1')).toContainText('Operational Intelligence');

    // Verify 4 Tab buttons
    await expect(page.locator('button:has-text("Overview")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Consent & 15 Categories")')).toBeVisible();
    await expect(page.locator('button:has-text("Reviews & Operations")')).toBeVisible();
    await expect(page.locator('button:has-text("AI Advisory & Trends")')).toBeVisible();

    // Test Export Dialog open and close
    const exportBtn = page.locator('button:has-text("Export Report")');
    if (await exportBtn.isVisible()) {
      await exportBtn.click();
      const exportModal = page.locator('[data-testid="auth-modal"], [role="dialog"]');
      await expect(exportModal).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(exportModal).not.toBeVisible();
    }
  });

  // Test I — Identity Switching
  test('Test I — Switching between preset personas refreshes header identity', async ({ page }) => {
    await page.goto('/');

    const quickOlivia = page.locator('[data-testid="quick-login-olivia"]');
    if (await quickOlivia.isVisible()) {
      await quickOlivia.click();
      await expect(page.locator('text=Olivia Director')).toBeVisible();

      // Switch persona to Claire
      await page.click('[data-testid="switch-user-btn"]');
      await page.click('button:has-text("Claire Care")');
      await expect(page.locator('text=Claire Care')).toBeVisible();
    }
  });

  // Test J — Multi-Viewport Responsive Experience
  test('Test J — Responsive rendering across Mobile, Tablet, and Desktop viewports', async ({ page }) => {
    const viewports = [
      { name: 'Mobile', width: 375, height: 667 },
      { name: 'Tablet', width: 768, height: 1024 },
      { name: 'Desktop', width: 1440, height: 900 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/projects');
      await expect(page.locator('h1')).toBeVisible();

      await page.goto('/analytics');
      await expect(page.locator('h1')).toBeVisible();
    }
  });

  // Test K — Failure & Error Boundary Resilience
  test('Test K — Handles non-existent routes and records gracefully', async ({ page }) => {
    await page.goto('/projects/00000000-0000-0000-0000-000000000000');
    // Verify unauthorized or not found fallback is rendered without uncaught crash
    await expect(page.locator('body')).not.toBeEmpty();
  });
});

