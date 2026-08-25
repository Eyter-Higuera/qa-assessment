import { Page, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class BookStorePage extends BasePage {
  readonly path = '/books';

  readonly searchBox = this.page.locator('#searchBox');
  readonly resultRows = this.page.locator('tbody tr');

  constructor(page: Page) {
    super(page);
  }

  async expectLoaded(): Promise<void> {
    await expect(this.searchBox).toBeVisible();
    // The catalogue is fetched client-side; wait for data, not for a fixed delay.
    await expect(this.resultRows.first()).toBeVisible();
  }

  async search(term: string): Promise<void> {
    await this.searchBox.fill(term);
  }

  bookLink(title: string) {
    return this.page.locator('tbody a', { hasText: title });
  }

  async openBook(title: string): Promise<void> {
    await this.bookLink(title).click();
  }

  async expectResultCount(count: number): Promise<void> {
    await expect(this.resultRows).toHaveCount(count);
  }

  /** Empty search results render a table with zero body rows. */
  async expectNoResults(): Promise<void> {
    await expect(this.resultRows).toHaveCount(0);
  }
}
