import { test, expect } from './fixtures';
import { SEEDED_BOOK } from '../src/utils/test-data';
import { sessionTokenFromBrowser } from '../src/utils/api-client';

/**
 * The end-to-end journey required by the assessment:
 *   register -> login -> search & add a book -> view collection -> delete -> logout
 *
 * It is written as ONE test because the steps are one user journey: splitting them
 * into five independent tests would either re-run the whole prefix five times or
 * leak state between tests. `test.step` keeps the report readable and pinpoints
 * which step failed.
 */
test.describe('Book Store - my collection @e2e', () => {
  test('a user can register, add a book to their collection, remove it and log out', async ({
    page,
    context,
    user,
    api,
    loginPage,
    bookStorePage,
    bookDetailPage,
    profilePage,
  }) => {
    await test.step('1. Register (account provisioned via API - see fixtures.ts)', async () => {
      expect(user.userId, 'the account should have been created').toBeTruthy();
    });

    await test.step('2. Log in through the UI', async () => {
      await loginPage.goto();
      await loginPage.expectLoaded();
      await loginPage.login(user.userName, user.password);
      await profilePage.expectLoadedFor(user.userName);
    });

    await test.step('3. Search for a book and add it to the collection', async () => {
      await bookStorePage.goto();
      await bookStorePage.expectLoaded();

      await bookStorePage.search(SEEDED_BOOK.title);
      await bookStorePage.expectResultCount(1);
      await expect(bookStorePage.bookLink(SEEDED_BOOK.title)).toBeVisible();

      await bookStorePage.openBook(SEEDED_BOOK.title);
      await bookDetailPage.expectLoadedFor(SEEDED_BOOK.isbn, SEEDED_BOOK.title);
      await bookDetailPage.addToCollection();
    });

    await test.step('4. The book appears in my collection', async () => {
      await profilePage.goto();
      await profilePage.expectLoadedFor(user.userName);
      await profilePage.expectBookInCollection(SEEDED_BOOK.title);
      await expect(profilePage.bookRow(SEEDED_BOOK.title)).toContainText(SEEDED_BOOK.author);

      // Cross-layer check: the UI and the API must agree about what was persisted.
      // Reuses the browser's own token - see sessionTokenFromBrowser() for why.
      const books = await api.getBooks(await sessionTokenFromBrowser(context), user.userId);
      expect(books.map((b) => b.isbn), 'API state must match what the UI shows').toEqual([SEEDED_BOOK.isbn]);
    });

    await test.step('5. Delete the book from my collection', async () => {
      await profilePage.deleteBook(SEEDED_BOOK.isbn);
      await profilePage.expectCollectionEmpty();

      const books = await api.getBooks(await sessionTokenFromBrowser(context), user.userId);
      expect(books, 'deletion must be persisted, not just hidden').toEqual([]);
    });

    await test.step('6. Log out', async () => {
      await profilePage.logout();
      await expect(page).toHaveURL(/\/login/);
      await loginPage.expectLoaded();

      // Logging out must actually end the session, not just redirect.
      await profilePage.goto();
      await expect(profilePage.notLoggedInMessage).toBeVisible();
    });
  });

  test('cancelling the delete dialog keeps the book in the collection @regression', async ({
    context,
    user,
    api,
    loginPage,
    profilePage,
  }) => {
    // This test owns "cancel delete", not "add book", so the precondition is
    // seeded through the API - fast, deterministic, and it cannot fail for a
    // reason that belongs to another test.
    const token = await api.generateToken(user.userName, user.password);
    await api.addBooks(token, user.userId, [SEEDED_BOOK.isbn]);

    await loginPage.goto();
    await loginPage.login(user.userName, user.password);
    await profilePage.expectLoadedFor(user.userName);
    await profilePage.expectBookInCollection(SEEDED_BOOK.title);

    await profilePage.cancelDeleteBook(SEEDED_BOOK.isbn);

    await profilePage.expectBookInCollection(SEEDED_BOOK.title);
    const remaining = await api.getBooks(await sessionTokenFromBrowser(context), user.userId);
    expect(remaining, 'cancel must not delete anything').toHaveLength(1);
  });
});
