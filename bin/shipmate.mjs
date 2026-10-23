#!/usr/bin/env node
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';
import { execSync } from 'node:child_process';

const ROOT = resolve(new URL('.', import.meta.url).pathname, '..');
const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));

const args = process.argv.slice(2);
const command = args[0] || 'help';

function runQuiet(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  } catch {
    return null;
  }
}

function hasBin(name) {
  return runQuiet(`which ${name}`) !== null;
}

const HARNESSES = [
  { id: 'claude', name: 'Claude Code', bin: 'claude', configDir: join(homedir(), '.claude') },
  { id: 'codex', name: 'OpenAI Codex CLI', bin: 'codex', configDir: join(homedir(), '.codex') },
  { id: 'omp', name: 'Oh-My-Pi (OMP)', bin: 'omp', configDir: join(homedir(), '.omp') },
  { id: 'pi', name: 'Pi Coding Agent', bin: 'pi', configDir: join(homedir(), '.pi') },
  { id: 'opencode', name: 'OpenCode', bin: 'opencode', configDir: join(homedir(), '.config/opencode') },
  { id: 'agy', name: 'Antigravity / Gemini CLI', bin: 'agy', configDir: join(homedir(), '.gemini') },
];

function printBanner() {
  console.log(`⚓ Shipmate v${pkg.version} — Multi-Harness Engineering Delivery Plugin`);
  console.log('Supported: Claude Code · Codex · Oh-My-Pi · OpenCode · Gemini/Agy · Cursor · Windsurf\n');
}

function doctor() {
  printBanner();
  console.log('Detecting harnesses:');
  for (const h of HARNESSES) {
    const installed = hasBin(h.bin);
    const hasConfig = existsSync(h.configDir);
    const status = installed ? '✔ INSTALLED' : hasConfig ? '○ Config dir found' : '✖ Not detected';
    console.log(`  ${h.name.padEnd(26)} : ${status}`);
  }
  console.log('\nPublic actions in this plugin:');
  console.log('  /specify     - Requirements and technical design interview -> reviewed specification');
  console.log('  /run         - Deliver local requirements to a verified draft pull request');
  console.log('  /review      - Multi-persona independent review challenging specifications, plans, diffs');
  console.log('  /walkthrough - Progressive layered explanation of a merge request or local change');
  console.log('  /quiz        - Diagnostic comprehension quiz and understanding report');
}

function listSkills() {
  printBanner();
  console.log('Available Shipmate Skills:');
  const skills = ['specify', 'run', 'review', 'walkthrough', 'quiz'];
  for (const s of skills) {
    const skillPath = join(ROOT, 'skills', s, 'SKILL.md');
    if (existsSync(skillPath)) {
      const text = readFileSync(skillPath, 'utf8');
      const desc = /^description: (.+)$/m.exec(text)?.[1] || '';
      console.log(`  • ${s.padEnd(12)}: ${desc}`);
    }
  }
}

function install(target = 'all') {
  printBanner();
  console.log(`Configuring Shipmate plugin for: ${target}...\n`);

  if (target === 'all' || target === 'claude') {
    if (hasBin('claude')) {
      console.log('Configuring Claude Code...');
      try {
        execSync(`claude plugin validate "${ROOT}"`, { stdio: 'inherit' });
        console.log('✔ Claude Code plugin manifest validated successfully.');
        console.log('  Run in your workspace: claude --plugin-dir ' + ROOT);
      } catch (err) {
        console.warn('  Notice: Claude plugin command exited with status:', err.status);
      }
    }
  }

  if (target === 'all' || target === 'omp' || target === 'pi') {
    if (hasBin('omp')) {
      console.log('\nConfiguring Oh-My-Pi (OMP)...');
      try {
        execSync(`omp plugin link "${ROOT}"`, { stdio: 'inherit' });
        console.log('✔ Oh-My-Pi plugin linked successfully.');
      } catch {
        console.log('  Use with OMP: omp --plugin-dir ' + ROOT);
      }
    } else if (hasBin('pi')) {
      console.log('\nConfiguring Pi...');
      try {
        execSync(`pi install "${ROOT}" -l`, { stdio: 'inherit' });
        console.log('✔ Pi package installed.');
      } catch {
        console.log('  Install into Pi using: pi install ' + ROOT);
      }
    }
  }

  if (target === 'all' || target === 'opencode') {
    const opencodeConfigPath = join(homedir(), '.config/opencode/opencode.json');
    if (existsSync(opencodeConfigPath)) {
      console.log('\nOpenCode configuration detected at ~/.config/opencode/opencode.json');
      console.log('  Shipmate exports ./opencode.mjs and conforms to the OpenCode v2 plugin API.');
      console.log('  Add to "plugins" in your opencode.json: "' + ROOT + '"');
    }
  }

  if (target === 'all' || target === 'cursor') {
    console.log('\nCursor:');
    console.log('  Cursor rules are pre-packaged at .cursorrules and .cursor/rules/');
    console.log('  Copy or link .cursorrules into your project to enable Shipmate in Cursor.');
  }

  if (target === 'all' || target === 'windsurf') {
    console.log('\nWindsurf:');
    console.log('  Windsurf workflows are pre-packaged in .windsurf/workflows/');
  }

  console.log('\nDone! Shipmate is ready for multi-harness operation.');
}

switch (command) {
  case 'doctor':
    doctor();
    break;
  case 'list':
    listSkills();
    break;
  case 'install':
    install(args[1] || 'all');
    break;
  case 'version':
  case '-v':
  case '--version':
    console.log(`v${pkg.version}`);
    break;
  case 'help':
  default:
    printBanner();
    console.log('Usage:');
    console.log('  shipmate doctor           Check detected harnesses and readiness');
    console.log('  shipmate list             List packaged skills and capabilities');
    console.log('  shipmate install [target] Configure plugin for a harness (claude, omp, pi, opencode, all)');
    console.log('  shipmate help             Show this help guide');
    break;
}
