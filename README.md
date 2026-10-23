# Shipmate Plugin Installation Guide

Shipmate delivers engineering work from Jira or local requirements, with multi-persona reviews, layered walkthroughs, and diagnostic quizzes for merge requests.

This guide explains how to install and activate Shipmate in each supported AI coding harness.

---

## 1. Anthropic Claude Code

### Install via Marketplace (Recommended)
Add the marketplace and install the plugin:
```bash
claude plugin marketplace add 4rankng/shipmate
claude plugin install shipmate@shipmate-marketplace
```

Or from within an active Claude Code session:
```text
/plugin install shipmate --marketplace 4rankng/shipmate
```

### Local Development / Workspace Load
Point Claude Code directly to the local checkout:
```bash
claude --plugin-dir /path/to/shipmate
```

### Validate Installation
```bash
claude plugin validate /path/to/shipmate
```

Once loaded, public slash commands `/specify`, `/run`, `/review`, `/walkthrough`, and `/quiz` are available immediately.

---

## 2. Oh-My-Pi (OMP) & Pi Coding Agent

### Oh-My-Pi (OMP)
Link the plugin locally into OMP:
```bash
omp plugin link /path/to/shipmate
```

Or launch an ephemeral session with the plugin:
```bash
omp --plugin-dir /path/to/shipmate
```

### Pi Coding Agent
Install the package into your project or user settings:
```bash
# Project-local install
pi install /path/to/shipmate -l

# Global user install
pi install /path/to/shipmate
```

Commands (`/specify`, `/run`, `/review`, `/walkthrough`, `/quiz`) and skills are enabled automatically.

---

## 3. OpenAI Codex CLI

Install the plugin through the Codex plugin manager:
```bash
codex plugin add /path/to/shipmate
```

Codex reads the manifest from `.codex-plugin/plugin.json` and configures the default agent actions (`$shipmate:specify`, `$shipmate:run`, `$shipmate:review`, `$shipmate:walkthrough`, `$shipmate:quiz`).

---

## 4. OpenCode

Add the plugin path to your `~/.config/opencode/opencode.json` (or project-level `opencode.json`):

```json
{
  "plugins": [
    "/path/to/shipmate"
  ]
}
```

OpenCode automatically loads `opencode.mjs` and registers the five skills:
* `shipmate:specify`
* `shipmate:run`
* `shipmate:review`
* `shipmate:walkthrough`
* `shipmate:quiz`

---

## 5. Google Antigravity & Gemini CLI

### Antigravity (`agy`)
Validate or link the plugin:
```bash
agy plugin validate /path/to/shipmate
agy plugin install /path/to/shipmate
```

### Gemini CLI (`gemini`)
```bash
gemini --extensions /path/to/shipmate
```

---

## 6. Cursor

Copy or symlink the pre-configured rules into your project root:
```bash
# From your project directory:
cp -r /path/to/shipmate/.cursor .
cp /path/to/shipmate/.cursorrules .
```

Cursor will automatically load the rules for specification, TDD execution, review, walkthroughs, and quizzes.

---

## 7. Windsurf (Cascade)

Copy the pre-configured Cascade workflows and rules:
```bash
# From your project directory:
cp -r /path/to/shipmate/.windsurf .
cp /path/to/shipmate/.windsurfrules .
```

Trigger `/specify`, `/run`, `/review`, `/walkthrough`, or `/quiz` directly in Cascade chat.

---

## 8. Continue.dev

Copy the custom slash command prompt templates to your Continue directory:
```bash
mkdir -p ~/.continue/prompts
cp /path/to/shipmate/.continue/prompts/*.prompt ~/.continue/prompts/
```

---

## 9. GitHub Copilot

Copy the Copilot instructions to your workspace:
```bash
mkdir -p .github
cp /path/to/shipmate/.github/copilot-instructions.md .github/
```

---

## Choosing an Action

| You want to… | Use |
|---|---|
| Turn a Jira ticket, local file, or rough task into a reviewed requirement contract | `/specify` |
| Take a settled requirement to a verified draft MR through TDD and review | `/run` |
| Get independent, evidence-bound challenge of a spec, plan, or candidate | `/review` |
| Understand a ticket or change in layers, with grounded diagrams | `/walkthrough` |
| Check your own understanding of a change before it reaches production | `/quiz` |

## Harness Support

| Harness | Slash commands | Adapter source | Notes |
|---|---|---|---|
| Claude Code | ✅ `/specify` `/run` `/review` `/walkthrough` `/quiz` | marketplace or `--plugin-dir` | validate with `claude plugin validate` |
| Oh-My-Pi / Pi | ✅ all five | plugin link / `pi install` | commands and skills auto-enabled |
| OpenAI Codex CLI | `$shipmate:*` agent actions | `.codex-plugin/` | manifest-validated |
| OpenCode | five skills auto-registered | `opencode.mjs` | add the path to `plugins` |
| Antigravity / Gemini CLI | plugin / extension load | `configs/antigravity-cli/` | validate with `agy plugin validate` |
| Cursor | rules (no slash commands) | `.cursor/rules/`, `.cursorrules` | trigger by intent in chat |
| Windsurf | workflows | `.windsurf/workflows/` | trigger `/specify` etc. in Cascade |
| Continue.dev | prompts | `~/.continue/prompts/` | copy from `.continue/prompts/` |
| GitHub Copilot | instructions | `.github/copilot-instructions.md` | capability routing only |

Every command, rule, workflow and prompt surface is **generated** from `skills/*/SKILL.md` by
`scripts/gen_adapters.py` — edit the skill, then regenerate. `gen_adapters.py --check` and
`stamp_version.py --check` run in CI, so hand-edited copies and version drift fail the build.

## Quick Setup Script

Shipmate provides an automated installer that checks for installed harnesses and sets up all configurations:

```bash
# Inspect detected harnesses
./bin/shipmate.mjs doctor

# Automatically install/configure for all detected harnesses
./bin/shipmate.mjs install all

# Or install for a specific harness (e.g. claude, omp, pi, opencode)
./bin/shipmate.mjs install claude
```
