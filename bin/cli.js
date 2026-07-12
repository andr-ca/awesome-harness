#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const path = require('node:path');

const HARNESS_ROOT = path.resolve(__dirname, '..');
const SCRIPT = path.join(HARNESS_ROOT, 'tools', 'setup', 'harness-link.sh');

function isAvailable(cmd) {
  const result = spawnSync(cmd, ['--version'], { stdio: 'ignore' });
  return result.error === undefined;
}

if (!isAvailable('bash')) {
  console.error(
    'agentharness requires bash, which was not found on PATH.\n' +
      'This CLI wraps a Bash script and only supports Linux/macOS ' +
      '(or WSL/Git Bash for Windows).'
  );
  process.exit(1);
}

if (!isAvailable('python3')) {
  console.error(
    'agentharness requires python3, which was not found on PATH.\n' +
      'tools/setup/harness-link.sh uses it to read/write ' +
      '.agentharness-state.json.'
  );
  process.exit(1);
}

const result = spawnSync('bash', [SCRIPT, ...process.argv.slice(2)], {
  stdio: 'inherit',
});

if (result.error) {
  console.error(`Failed to run ${SCRIPT}: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status === null ? 1 : result.status);
