#!/usr/bin/env node
/**
 * Run the CI pipeline locally, with the same stages, gates and parameters.
 *
 *   node scripts/pipeline.mjs --stage dev --suite smoke --browser chromium
 *
 * Why this exists rather than `act`: act runs the real workflow, but it needs
 * Docker, and the workflow's value is in its ORDER and PARAMETERS, not in the
 * runner image. This reproduces both without a container, on any platform. See
 * .github/act/ for the act route if you do have Docker.
 *
 * Design notes, because two real bugs in this repository came from shells:
 *
 *  - Every command is spawned with an argv array and `shell: false`. No shell
 *    parses these arguments, so `@smoke` cannot be eaten by PowerShell's
 *    splatting operator and nothing depends on quoting rules that differ
 *    between cmd, PowerShell and bash.
 *  - Node cannot spawn a .cmd shim with shell:false, so the Node tools are
 *    invoked as `node <package>/cli.js` and only Maven goes through a shell.
 *  - Paths resolve from this file, never from process.cwd(), so it behaves the
 *    same run from the repository root or from any subdirectory.
 *  - Inputs are checked against allow-lists before use; nothing reaches a
 *    command line unvalidated.
 */
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const PW = join(ROOT, 'playwright');
const KARATE = join(ROOT, 'karate');
const DEMO = 'https://demoqa.com';

/** stage -> the environment variable consulted first, then the fallback host. */
const STAGES = {
  dev: { vars: ['DEV_BASE_URL', 'STAGING_BASE_URL'], fallback: DEMO, karateEnv: 'dev' },
  release: { vars: ['RELEASE_BASE_URL'], fallback: DEMO, karateEnv: 'release' },
  production: { vars: ['PRODUCTION_BASE_URL'], fallback: DEMO, karateEnv: 'production' },
};

/** suite -> which layers run, and how much of each. */
const SUITES = {
  unit: { layers: ['unit'], depth: 'all' },
  api: { layers: ['api'], depth: 'all' },
  ui: { layers: ['ui'], depth: 'all' },
  smoke: { layers: ['unit', 'api', 'ui'], depth: 'smoke' },
  regression: { layers: ['unit', 'api', 'ui'], depth: 'all' },
};

const BROWSERS = ['chromium', 'firefox', 'webkit', 'msedge'];

// Network-bound layers get one retry: demoqa has been measured answering a
// login in 25-30s, and a single slow response should not read as a red suite.
const RETRIES = { unit: 0, api: 1, ui: 1 };
const TIMEOUT_MS = { unit: 5 * 60_000, api: 15 * 60_000, ui: 30 * 60_000 };

/**
 * Quote one argument for a cmd.exe command line. Everything passed here is
 * already allow-list validated except BASE_URL, which comes from the
 * environment and could contain anything.
 */
function winQuote(arg) {
  return /[\s"^&|<>()]/.test(arg) ? `"${arg.replace(/(["\\])/g, '\\$1')}"` : arg;
}

function fail(message) {
  console.error(`\n  ${message}\n`);
  process.exit(2);
}

function parseArgs(argv) {
  const opts = { stage: 'dev', suite: 'smoke', browser: 'chromium', dryRun: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dry-run') { opts.dryRun = true; continue; }
    if (arg === '--help' || arg === '-h') { usage(); process.exit(0); }
    const match = /^--(stage|suite|browser)(?:=(.*))?$/.exec(arg);
    if (!match) fail(`unrecognised argument "${arg}". Try --help.`);
    const value = match[2] ?? argv[++i];
    if (value === undefined) fail(`--${match[1]} needs a value.`);
    opts[match[1]] = value;
  }
  // Validate before anything reaches a command line.
  if (!STAGES[opts.stage]) fail(`--stage must be one of: ${Object.keys(STAGES).join(', ')}`);
  if (!SUITES[opts.suite]) fail(`--suite must be one of: ${Object.keys(SUITES).join(', ')}`);
  if (opts.browser !== 'all' && !BROWSERS.includes(opts.browser)) {
    fail(`--browser must be one of: ${BROWSERS.join(', ')}, all`);
  }
  return opts;
}

function usage() {
  console.log(`
  Local pipeline runner — mirrors .github/workflows/ci.yml

    node scripts/pipeline.mjs [--stage S] [--suite T] [--browser B] [--dry-run]

    --stage    ${Object.keys(STAGES).join(' | ')}            (default dev)
    --suite    ${Object.keys(SUITES).join(' | ')}   (default smoke)
    --browser  ${BROWSERS.join(' | ')} | all         (default chromium)

  Layers run in the CI order and stop at the first failure:

    unit (Vitest)  ->  api (Karate)  ->  ui (Playwright)

  unit, api and ui each run that layer alone; smoke and regression run all
  three, shallow or deep. The host comes from ${Object.values(STAGES)
    .flatMap((s) => s.vars).join(', ')} or falls back to ${DEMO}.
`);
}

function baseUrlFor(stage) {
  const { vars, fallback } = STAGES[stage];
  for (const name of vars) {
    const value = process.env[name];
    if (value) return { url: value, from: name };
  }
  return { url: fallback, from: 'default' };
}

function nodeBin(...parts) {
  const path = join(PW, 'node_modules', ...parts);
  if (!existsSync(path)) {
    fail(`${parts.join('/')} is missing. Run "npm ci" in playwright/ first.`);
  }
  return path;
}

/**
 * Spawn and wait. `shell` is false for everything except Maven, whose Windows
 * entry point is a .cmd that Node refuses to spawn directly.
 */
function run(label, spec) {
  const { command, args, cwd, env = {}, shell = false, timeout } = spec;
  return new Promise((resolvePromise) => {
    const started = Date.now();
    const shown = spec.display ?? `${command === process.execPath ? 'node' : command} ${args.join(' ')}`;
    console.log(`\n  $ ${shown}`);
    console.log(`    (in ${cwd.replace(ROOT, '.')})`);
    const child = spawn(command, args, {
      cwd,
      shell,
      stdio: 'inherit',
      // An explicit child environment: the run must not depend on whatever the
      // caller happened to export, beyond what is deliberately passed in.
      env: { ...process.env, ...env },
    });
    const timer = timeout && setTimeout(() => {
      console.error(`\n  ${label} exceeded ${Math.round(timeout / 60000)} minutes — killing it.`);
      child.kill('SIGTERM');
    }, timeout);
    child.on('close', (code) => {
      if (timer) clearTimeout(timer);
      resolvePromise({ code: code ?? 1, seconds: (Date.now() - started) / 1000 });
    });
    child.on('error', (err) => {
      if (timer) clearTimeout(timer);
      console.error(`  could not start ${command}: ${err.message}`);
      resolvePromise({ code: 127, seconds: (Date.now() - started) / 1000 });
    });
  });
}

async function runWithRetry(label, spec, retries) {
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    if (attempt) console.log(`\n  retrying ${label} (attempt ${attempt + 1} of ${retries + 1})`);
    const result = await run(label, spec);
    if (result.code === 0 || attempt === retries) return result;
  }
  return { code: 1, seconds: 0 };
}

function step(layer, { stage, suite, browser, baseUrl }) {
  const depth = SUITES[suite].depth;
  const karateEnv = STAGES[stage].karateEnv;

  if (layer === 'unit') {
    return {
      command: process.execPath,
      args: [nodeBin('vitest', 'vitest.mjs'), 'run', '--coverage'],
      cwd: PW,
      timeout: TIMEOUT_MS.unit,
    };
  }
  if (layer === 'api') {
    const runner = depth === 'smoke' ? 'SmokeTest' : 'BookStoreApiTest';
    const mvnArgs = ['-B', 'test', `-Dtest=${runner}`,
      `-Dkarate.env=${karateEnv}`, `-DbaseUrl=${baseUrl}`];
    if (process.platform !== 'win32') {
      return { command: 'mvn', args: mvnArgs, cwd: KARATE, timeout: TIMEOUT_MS.api };
    }
    // Maven's Windows entry point is a .cmd, which Node refuses to spawn
    // without a shell. Handing an args array to `shell: true` is exactly what
    // Node deprecated in DEP0190 — it concatenates without escaping. So the
    // command line is quoted here and passed to cmd.exe as a single argument
    // with shell:false, which is the escaping-safe form of the same call.
    return {
      command: process.env.ComSpec || 'cmd.exe',
      args: ['/d', '/s', '/c', `mvn ${mvnArgs.map(winQuote).join(' ')}`],
      cwd: KARATE,
      timeout: TIMEOUT_MS.api,
      display: `mvn ${mvnArgs.join(' ')}`,
    };
  }
  const projects = browser === 'all' ? BROWSERS : [browser];
  const args = [nodeBin('playwright', 'cli.js'), 'test', ...projects.map((p) => `--project=${p}`)];
  // No shell sees this, so the tag needs no quoting and cannot be swallowed.
  if (depth === 'smoke') args.push('--grep', '@smoke');
  return {
    command: process.execPath,
    args,
    cwd: PW,
    env: { BASE_URL: baseUrl },
    timeout: TIMEOUT_MS.ui,
  };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const { url: baseUrl, from } = baseUrlFor(opts.stage);
  const layers = SUITES[opts.suite].layers;

  console.log('\n  Local pipeline');
  console.log(`    stage    ${opts.stage}  (BASE_URL ${baseUrl} — from ${from})`);
  console.log(`    suite    ${opts.suite}  → ${layers.join(' → ')}`);
  console.log(`    browser  ${opts.browser === 'all' ? BROWSERS.join(', ') : opts.browser}`);

  const results = [];
  for (const layer of layers) {
    const spec = step(layer, { ...opts, baseUrl });
    if (opts.dryRun) {
      const shown = spec.display
        ?? `${spec.command === process.execPath ? 'node' : spec.command} ${spec.args.join(' ')}`;
      console.log(`\n  [dry run] ${layer}: ${shown}`);
      results.push({ layer, code: 0, seconds: 0 });
      continue;
    }
    const result = await runWithRetry(layer, spec, RETRIES[layer] ?? 0);
    results.push({ layer, ...result });
    if (result.code !== 0) {
      console.error(`\n  ${layer} failed (exit ${result.code}) — later layers skipped, as CI would.`);
      break;
    }
  }

  console.log('\n  Summary');
  for (const { layer, code, seconds } of results) {
    console.log(`    ${layer.padEnd(6)} ${code === 0 ? 'passed' : `FAILED (exit ${code})`}  ${seconds.toFixed(1)}s`);
  }
  const skipped = layers.filter((l) => !results.some((r) => r.layer === l));
  if (skipped.length) console.log(`    ${skipped.join(', ')} skipped`);

  process.exit(results.some((r) => r.code !== 0) ? 1 : 0);
}

main();
