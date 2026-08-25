import { randomUUID } from 'node:crypto';

/**
 * Unique credentials per test run.
 *
 * The Book Store account namespace is global and shared with every other person
 * using demoqa.com, so a fixed username would collide (`1204 User exists!`) and
 * make the suite fail for reasons that have nothing to do with the product.
 * Password satisfies the documented policy: 8+ chars, upper, lower, digit, symbol.
 */
export function uniqueUser(prefix = 'qa'): { userName: string; password: string } {
  return {
    userName: `${prefix}_${randomUUID().slice(0, 8)}`,
    password: 'Passw0rd!23',
  };
}

/** A book that exists in the seeded catalogue; used as the happy-path fixture. */
export const SEEDED_BOOK = {
  isbn: '9781449325862',
  title: 'Git Pocket Guide',
  author: 'Richard E. Silverman',
  publisher: "O'Reilly Media",
};
