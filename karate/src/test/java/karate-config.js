/**
 * Global Karate configuration.
 *
 * `karate.env` selects the target environment (mvn test -Dkarate.env=staging), so
 * the same suite runs against a local stack, a shared test environment, or the
 * public demo without a single edit to a feature file.
 */
function fn() {
  var env = karate.env || 'dev';
  karate.log('karate.env =', env);

  var config = {
    env: env,
    baseUrl: 'https://demoqa.com',
    // Meets the documented policy: 8+ chars, upper, lower, digit, special.
    defaultPassword: 'Passw0rd!23',
    // A book that exists in the seeded catalogue.
    seededIsbn: '9781449325862',
    seededTitle: 'Git Pocket Guide',
    secondIsbn: '9781449331818'
  };

  // One entry per environment in the promotion chain, plus the two a developer
  // uses by hand. CI always passes the real host with -DbaseUrl=..., so these
  // literals are only the fallback for `mvn test -Dkarate.env=release` locally.
  var defaultHosts = {
    dev: 'https://demoqa.com',
    staging: 'https://staging.example.com',
    release: 'https://release.example.com',
    production: 'https://demoqa.com',
    local: 'http://localhost:3000'
  };
  if (!defaultHosts[env]) {
    // A typo in -Dkarate.env would otherwise run the whole suite against the
    // default host and report a pass for an environment nobody tested.
    karate.fail('unknown karate.env: ' + env);
  }
  config.baseUrl = karate.properties['baseUrl'] || defaultHosts[env];

  // Fail fast rather than hang when an environment is down.
  karate.configure('connectTimeout', 10000);
  karate.configure('readTimeout', 30000);
  // Retry helper for the few genuinely async endpoints; used via `retry until`.
  karate.configure('retry', { count: 3, interval: 2000 });

  return config;
}
