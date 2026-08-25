import { Page, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class BookDetailPage extends BasePage {
  readonly path = '/books';

  /**
   * NOTE: the app renders *two* buttons with id="addNewRecordButton"
   * ("Back To Book Store" and "Add To Your Collection"). Selecting by id would be
   * ambiguous, so these are addressed by accessible name instead - which is also
   * what a real user perceives. Filed as BUG-002 in Senior_QA_Engineer_Assessment.md (Appendix B).
   */
  readonly addToCollectionButton = this.page.getByRole('button', { name: 'Add To Your Collection' });
  readonly backToStoreButton = this.page.getByRole('button', { name: 'Back To Book Store' });
  readonly isbnWrapper = this.page.locator('#ISBN-wrapper');

  constructor(page: Page) {
    super(page);
  }

  async gotoIsbn(isbn: string): Promise<void> {
    await this.page.goto(`/books?search=${isbn}`, { waitUntil: 'domcontentloaded' });
    await this.suppressAds();
  }

  async expectLoadedFor(isbn: string, title: string): Promise<void> {
    await expect(this.isbnWrapper).toContainText(isbn);
    await expect(this.page.getByText(title, { exact: true }).first()).toBeVisible();
  }

  /** Adds the book and asserts the confirmation alert the app raises. */
  async addToCollection(): Promise<void> {
    await this.clickAndAcceptDialog(this.addToCollectionButton, /Book added to your collection/i);
  }

  /** Adding the same ISBN twice surfaces the API's 1210 error through an alert. */
  async addToCollectionExpectingDuplicate(): Promise<void> {
    await this.clickAndAcceptDialog(this.addToCollectionButton, /already present/i);
  }
}
