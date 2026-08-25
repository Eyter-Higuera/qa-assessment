import { test as base } from '@playwright/test';
import { ApiClient, TestUser } from '../src/utils/api-client';
import { uniqueUser } from '../src/utils/test-data';
import { LoginPage } from '../src/pages/LoginPage';
import { BookStorePage } from '../src/pages/BookStorePage';
import { BookDetailPage } from '../src/pages/BookDetailPage';
import { ProfilePage } from '../src/pages/ProfilePage';

type Fixtures = {
  api: ApiClient;
  /** A freshly registered, empty account - created before the test, removed after. */
  user: TestUser;
  loginPage: LoginPage;
  bookStorePage: BookStorePage;
  bookDetailPage: BookDetailPage;
  profilePage: ProfilePage;
};

export const test = base.extend<Fixtures>({
  api: async ({}, use) => {
    const api = await ApiClient.create();
    await use(api);
    await api.dispose();
  },

  /**
   * Registration fixture.
   *
   * The UI registration form is protected by Google reCAPTCHA, which cannot be
   * solved by an automated browser and must not be bypassed with hacks that only
   * work against the demo site. Registration is therefore performed against the
   * public API - the same account the user would have got from the form - and the
   * UI test starts from login. See Senior_QA_Engineer_Assessment.md,
   * Appendix A -> "Known constraints".
   */
  user: async ({ api }, use) => {
    const { userName, password } = uniqueUser();
    const created = await api.createUser(userName, password);
    await use(created);
    // Teardown: leave no residue behind, even if the test failed.
    const token = await api.generateToken(userName, password).catch(() => '');
    if (token) await api.deleteUser(token, created.userId);
  },

  loginPage: async ({ page }, use) => use(new LoginPage(page)),
  bookStorePage: async ({ page }, use) => use(new BookStorePage(page)),
  bookDetailPage: async ({ page }, use) => use(new BookDetailPage(page)),
  profilePage: async ({ page }, use) => use(new ProfilePage(page)),
});

export { expect } from '@playwright/test';
