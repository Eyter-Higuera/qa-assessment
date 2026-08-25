import { APIRequestContext, request } from '@playwright/test';

export interface TestUser {
  userName: string;
  password: string;
  userId: string;
}

/**
 * Thin client over the Book Store REST API.
 *
 * It exists for *test data management*, not for assertions: creating and tearing
 * down users through the API keeps UI tests focused on the behaviour they own and
 * removes the reCAPTCHA-protected registration form from the critical path.
 * (See docs/test-plan.md ("Registration & reCAPTCHA") for the rationale.)
 */
export class ApiClient {
  private constructor(private readonly ctx: APIRequestContext) {}

  static async create(baseURL = process.env.API_URL ?? 'https://demoqa.com'): Promise<ApiClient> {
    const ctx = await request.newContext({
      baseURL,
      extraHTTPHeaders: { 'Content-Type': 'application/json' },
      timeout: 30_000,
    });
    return new ApiClient(ctx);
  }

  async dispose(): Promise<void> {
    await this.ctx.dispose();
  }

  /** Creates a user. Throws on anything other than 201 so setup failures are loud. */
  async createUser(userName: string, password: string): Promise<TestUser> {
    const res = await this.ctx.post('/Account/v1/User', { data: { userName, password } });
    if (res.status() !== 201) {
      throw new Error(`Test-data setup failed: POST /Account/v1/User -> ${res.status()} ${await res.text()}`);
    }
    const body = await res.json();
    return { userName, password, userId: body.userID };
  }

  async generateToken(userName: string, password: string): Promise<string> {
    const res = await this.ctx.post('/Account/v1/GenerateToken', { data: { userName, password } });
    const body = await res.json();
    if (!body.token) {
      throw new Error(`Token generation failed for ${userName}: ${JSON.stringify(body)}`);
    }
    return body.token;
  }

  /**
   * Reads a user's collection.
   *
   * Throws on a non-200 so an expired/invalidated token surfaces as "auth broke"
   * rather than silently degrading to "the collection is empty" - which would turn
   * a real failure into a passing assertion.
   */
  async getBooks(token: string, userId: string): Promise<Array<{ isbn: string; title: string }>> {
    const res = await this.ctx.get(`/Account/v1/User/${userId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status() !== 200) {
      throw new Error(`GET /Account/v1/User/${userId} -> ${res.status()} ${await res.text()}`);
    }
    return (await res.json()).books ?? [];
  }

  /** Seeds a collection directly, so UI tests that are *not* about adding books can skip that path. */
  async addBooks(token: string, userId: string, isbns: string[]): Promise<void> {
    const res = await this.ctx.post('/BookStore/v1/Books', {
      headers: { Authorization: `Bearer ${token}` },
      data: { userId, collectionOfIsbns: isbns.map((isbn) => ({ isbn })) },
    });
    if (res.status() !== 201) {
      throw new Error(`Test-data setup failed: POST /BookStore/v1/Books -> ${res.status()} ${await res.text()}`);
    }
  }

  /** Best-effort cleanup: teardown must never fail a green test run. */
  async deleteUser(token: string, userId: string): Promise<void> {
    try {
      await this.ctx.delete(`/Account/v1/User/${userId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      /* ignored on purpose - the account is disposable */
    }
  }
}

/**
 * Returns the bearer token the *browser* is currently using.
 *
 * The Book Store back end keeps a single valid token per user: calling
 * `GenerateToken` again invalidates the one the UI session holds, which silently
 * logs the browser out mid-test. Cross-layer assertions therefore reuse the
 * session the UI already established instead of minting a competing one.
 * (See docs/defects.md BUG-009.)
 */
export async function sessionTokenFromBrowser(context: import('@playwright/test').BrowserContext): Promise<string> {
  const cookie = (await context.cookies()).find((c) => c.name === 'token');
  if (!cookie?.value) throw new Error('No session token cookie found - is the browser actually logged in?');
  return decodeURIComponent(cookie.value);
}
