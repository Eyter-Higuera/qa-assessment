import { test, expect } from './fixtures';

/**
 * Registration is protected by Google reCAPTCHA. Solving or bypassing it would
 * only work against this demo site and would give false confidence, so the UI
 * suite asserts the *contract of the form* and the happy path is covered through
 * the API instead (see Senior_QA_Engineer_Assessment.md, Appendix A ->
 * "Known constraints").
 */
test.describe('Registration @smoke', () => {
  test('the registration form is reachable from login and is captcha-protected', async ({
    page,
    loginPage,
  }) => {
    await loginPage.goto();
    await loginPage.newUserButton.click();
    await expect(page).toHaveURL(/\/register/);

    await expect(page.locator('#firstname')).toBeVisible();
    await expect(page.locator('#lastname')).toBeVisible();
    await expect(page.locator('#userName')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Register' })).toBeVisible();

    // Documents the automation boundary explicitly rather than silently skipping it.
    await expect(
      page.locator('iframe[src*="recaptcha"]').first(),
      'registration is gated by reCAPTCHA - happy path is covered via the API suite',
    ).toBeAttached();
  });

  test('the API rejects a password that violates the documented policy', async ({ api }) => {
    // Guards the rule the UI form is supposed to enforce for real users.
    await expect(api.createUser(`qa_weak_${Date.now()}`, 'abc')).rejects.toThrow(/400/);
  });
});
