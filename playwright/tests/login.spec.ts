import { test, expect } from './fixtures';

test.describe('Login @smoke', () => {
  test('rejects unknown credentials with a visible error and no session', async ({
    page,
    loginPage,
    profilePage,
  }) => {
    await loginPage.goto();
    await loginPage.login('no_such_user_9f3a1c', 'Wrong!123');

    await loginPage.expectError('Invalid username or password!');
    await expect(page, 'a failed login must not navigate away from /login').toHaveURL(/\/login/);

    await profilePage.goto();
    await expect(profilePage.notLoggedInMessage).toBeVisible();
  });

  test('rejects a valid username with the wrong password', async ({ user, loginPage, page }) => {
    await loginPage.goto();
    await loginPage.login(user.userName, 'Definitely!Wrong9');

    await loginPage.expectError('Invalid username or password!');
    await expect(page).toHaveURL(/\/login/);
  });

  test('protects the profile page from anonymous access', async ({ profilePage }) => {
    await profilePage.goto();
    await expect(profilePage.notLoggedInMessage).toBeVisible();
  });
});
