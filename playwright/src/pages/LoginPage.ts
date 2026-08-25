import { Page, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class LoginPage extends BasePage {
  readonly path = '/login';

  readonly userName = this.page.locator('#userName');
  readonly password = this.page.locator('#password');
  readonly loginButton = this.page.locator('#login');
  readonly newUserButton = this.page.locator('#newUser');
  readonly errorMessage = this.page.locator('#name');

  constructor(page: Page) {
    super(page);
  }

  async login(userName: string, password: string): Promise<void> {
    await this.userName.fill(userName);
    await this.password.fill(password);
    await this.loginButton.click();
  }

  async expectLoaded(): Promise<void> {
    await expect(this.userName).toBeVisible();
    await expect(this.loginButton).toBeVisible();
  }

  async expectError(text: string | RegExp): Promise<void> {
    await expect(this.errorMessage).toHaveText(text);
  }
}
