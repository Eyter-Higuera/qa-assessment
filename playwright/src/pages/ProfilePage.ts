import { Page, expect } from '@playwright/test';
import { BasePage, LOGIN_RESPONSE_TIMEOUT } from './BasePage';

export class ProfilePage extends BasePage {
  readonly path = '/profile';

  readonly userNameValue = this.page.locator('#userName-value').first();
  readonly searchBox = this.page.locator('#searchBox');
  readonly rows = this.page.locator('tbody tr');
  readonly notLoggedInMessage = this.page.getByText(/not logged into the Book Store application/i);

  /**
   * The app reuses id="submit" for Logout, Delete Account and Delete All Books
   * (BUG-001). Role + accessible name keeps this unambiguous and survives the
   * label drifting between "Logout" and "Log out" across pages.
   */
  readonly logoutButton = this.page.getByRole('button', { name: /log ?out/i });

  readonly deleteModal = this.page.getByRole('dialog');
  readonly confirmDeleteButton = this.page.locator('#closeSmallModal-ok');
  readonly cancelDeleteButton = this.page.locator('#closeSmallModal-cancel');

  constructor(page: Page) {
    super(page);
  }

  /**
   * Waits for the *authenticated* profile, not merely for the URL.
   * The page briefly renders its logged-out panel while the session is restored
   * (BUG-005), so asserting on the URL alone produces false failures.
   */
  async expectLoadedFor(userName: string): Promise<void> {
    await expect(this.page).toHaveURL(/\/profile/, { timeout: LOGIN_RESPONSE_TIMEOUT });
    await expect(this.userNameValue).toHaveText(userName);
  }

  bookRow(title: string) {
    return this.rows.filter({ hasText: title });
  }

  async expectBookInCollection(title: string): Promise<void> {
    await expect(this.bookRow(title), `"${title}" should be in the collection`).toHaveCount(1);
  }

  async expectCollectionEmpty(): Promise<void> {
    await expect(this.rows).toHaveCount(0);
  }

  /** Deletes a book by ISBN and confirms the modal + the resulting alert. */
  async deleteBook(isbn: string): Promise<void> {
    await this.page.locator(`#delete-record-${isbn}`).click();
    await expect(this.deleteModal).toBeVisible();
    await expect(this.deleteModal).toContainText('Do you want to delete this book?');
    await this.clickAndAcceptDialog(this.confirmDeleteButton, /Book deleted/i);
  }

  async cancelDeleteBook(isbn: string): Promise<void> {
    await this.page.locator(`#delete-record-${isbn}`).click();
    await expect(this.deleteModal).toBeVisible();
    await this.cancelDeleteButton.click();
    await expect(this.deleteModal).toBeHidden();
  }

  async logout(): Promise<void> {
    await this.logoutButton.click();
  }
}
