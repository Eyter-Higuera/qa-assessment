import { Locator, Page, expect } from '@playwright/test';

/**
 * Shared behaviour for every page object.
 *
 * demoqa.com serves third-party ad frames that float over the page and steal
 * clicks. Two defences, in order of effectiveness:
 *
 *  1. `blockAds()` aborts ad requests at the network layer, before they load.
 *     This is the one that matters: those requests also delay `domcontentloaded`,
 *     so blocking them fixes navigation timeouts as well as stolen clicks.
 *  2. `suppressAds()` sweeps up whatever still made it into the DOM.
 *
 * The DOM sweep alone is not enough - it runs once per navigation, while demoqa
 * injects ad frames asynchronously *after* that, and the resulting reflow keeps
 * elements from ever settling into an actionable state.
 */
export abstract class BasePage {
  /** Hosts that serve the ad frames and trackers demoqa embeds. */
  private static readonly AD_HOSTS = [
    'googlesyndication.com',
    'doubleclick.net',
    'googleadservices.com',
    'googletagservices.com',
    'google-analytics.com',
    'googletagmanager.com',
    'adsafeprotected.com',
    'moatads.com',
  ];

  /** Routing is per-page and must only be installed once. */
  private static readonly routed = new WeakSet<Page>();

  protected constructor(protected readonly page: Page) {}

  abstract readonly path: string;

  async goto(): Promise<void> {
    await this.blockAds();
    await this.page.goto(this.path, { waitUntil: 'domcontentloaded' });
    await this.suppressAds();
  }

  /** Aborts ad/tracker requests so they never load, never reflow and never delay navigation. */
  private async blockAds(): Promise<void> {
    if (BasePage.routed.has(this.page)) return;
    BasePage.routed.add(this.page);

    await this.page.route('**/*', (route) => {
      const url = route.request().url();
      return BasePage.AD_HOSTS.some((host) => url.includes(host)) ? route.abort() : route.continue();
    });
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
