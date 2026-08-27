import { describe, it, expect } from 'vitest';
import { uniqueUser, SEEDED_BOOK } from './test-data';

/**
 * These cover the two properties the whole suite quietly depends on.
 *
 * Both fail the same ugly way in an end-to-end run: a `1204 User exists!` or a
 * `1300 Passwords must have...` from the live API, several minutes in, pointing
 * at registration rather than at the helper that produced the credentials. A
 * unit test names the cause in milliseconds instead.
 */
describe('uniqueUser', () => {
  it('defaults to the qa prefix', () => {
    expect(uniqueUser().userName).toMatch(/^qa_/);
  });

  it('honours a caller-supplied prefix', () => {
    expect(uniqueUser('smoke').userName).toMatch(/^smoke_/);
  });

  it('never repeats a username', () => {
    // The Book Store account namespace is global and shared with everyone else
    // using demoqa.com, so a repeat is not a cosmetic problem - it is a failed
    // registration and a red suite.
    const names = new Set(Array.from({ length: 500 }, () => uniqueUser().userName));
    expect(names.size).toBe(500);
  });

  it('produces a password meeting the documented policy', () => {
    // demoqa documents: 8+ characters, upper, lower, digit, special. The API
    // rejects anything less with 1300, which reads as a test bug rather than a
    // data bug unless something asserts the policy here.
    const { password } = uniqueUser();
    expect(password.length).toBeGreaterThanOrEqual(8);
    expect(password).toMatch(/[A-Z]/);
    expect(password).toMatch(/[a-z]/);
    expect(password).toMatch(/[0-9]/);
    expect(password).toMatch(/[^A-Za-z0-9]/);
  });

  it('keeps usernames within what the registration form accepts', () => {
    expect(uniqueUser().userName.length).toBeLessThanOrEqual(32);
  });
});

describe('SEEDED_BOOK', () => {
  it('carries a 13-digit ISBN', () => {
    // The catalogue is searched by this value; a typo yields an empty result set
    // and an assertion failure three steps into the e2e journey.
    expect(SEEDED_BOOK.isbn).toMatch(/^\d{13}$/);
  });

  it('has every field the detail page asserts on', () => {
    for (const field of ['isbn', 'title', 'author', 'publisher'] as const) {
      expect(SEEDED_BOOK[field], `SEEDED_BOOK.${field}`).toBeTruthy();
    }
  });
});
