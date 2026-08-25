import { Locator, Page, expect } from '@playwright/test';

/**
 * Shared behaviour for every page object.
 *
 * demoqa.com serves third-party ad frames that float over the page and steal
 * clicks. `suppressAds()` removes them after navigation, which is the difference
 * between a suite that fails ~1 run in 5 and one that doesn't.
 */
export abstract class BasePage {
  protected constructor(protected readonly page: Page) {}

  abstract readonly path: string;

  async goto(): Promise<void> {
    await this.page.goto(this.path, { waitUntil: 'domcontentloaded' });
    await this.suppressAds();
  }

  /** Removes ad containers and the sticky footer banner that intercept pointer events. */
  async suppressAds(): Promise<void> {
    await this.page
      .evaluate(() => {
        const selectors = ['#fixedban', '#adplus-anchor', 'footer', 'iframe[id^="google_ads"]', '.adsbygoogle'];
        selectors.forEach((s) => document.querySelectorAll(s).forEach((el) => el.remove()));
      })
      .catch(() => {
        /* page may still be navigating - not worth failing a test over */
      });
  }

  /**
   * Clicks and waits for the JS alert the app raises, asserting its text.
   * The alert must be handled *while* the click is in flight, otherwise the
   * click promise never settles.
   */
  protected async clickAndAcceptDialog(target: Locator, expectedMessage: RegExp): Promise<void> {
    const dialog = this.page.waitForEvent('dialog');
    await target.click();
    const d = await dialog;
    expect(d.message(), 'unexpected browser dialog text').toMatch(expectedMessage);
    await d.accept();
  }
}
