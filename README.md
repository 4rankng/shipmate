# Shipmate Plugin Installation Guide

Shipmate is an engineering workflow harness built for solo developers and indie developers who
create software applications alone. It delivers work from local requirements with independent
multi-persona AI reviews, layered walkthroughs, diagnostic quizzes, Socratic interrogation, and end-to-end
UI/UX design review — the engineering team you
don't have, on demand.

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

Once loaded, public slash commands `/specify`, `/plan`, `/run`, `/review`, `/walkthrough`, `/quiz`, `/ask`, and `/uiux` are available immediately.

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

Commands (`/specify`, `/plan`, `/run`, `/review`, `/walkthrough`, `/quiz`, `/ask`, `/uiux`) and skills are enabled automatically.

---

## 3. OpenAI Codex CLI

Install the plugin through the Codex plugin manager:
```bash
codex plugin add /path/to/shipmate
```

Codex reads the manifest from `.codex-plugin/plugin.json` and configures the default agent actions (`$shipmate:specify`, `$shipmate:run`, `$shipmate:review`, `$shipmate:walkthrough`, `$shipmate:quiz`, `$shipmate:ask`, `$shipmate:uiux`).

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

OpenCode automatically loads `opencode.mjs` and registers the eight skills:
* `shipmate:specify`
* `shipmate:plan`
* `shipmate:run`
* `shipmate:review`
* `shipmate:walkthrough`
* `shipmate:quiz`
* `shipmate:ask`
* `shipmate:uiux`

The repository also ships `.agents/skills/` — the cross-harness discovery directory scanned
natively by OpenAI Codex CLI and opencode — so cloning this repo gives you all eight skills in
those harnesses with zero installation.

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

Cursor will automatically load the rules for specification, TDD execution, review, walkthroughs, quizzes, and diagnostic interrogation.

---

## 7. Windsurf (Cascade)

Copy the pre-configured Cascade workflows and rules:
```bash
# From your project directory:
cp -r /path/to/shipmate/.windsurf .
cp /path/to/shipmate/.windsurfrules .
```

Trigger `/specify`, `/plan`, `/run`, `/review`, `/walkthrough`, `/quiz`, `/ask`, or `/uiux` directly in Cascade chat.

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
| Turn a local requirement file or rough task into a reviewed requirement contract | `/specify` |
| Take a settled requirement to a verified draft PR or reviewed local commit through TDD and review | `/run` |
| Turn any requirement, task, or rough idea into a reviewed, proportionate implementation plan before coding | `/plan` |
| Get independent, evidence-bound challenge of a spec, plan, or candidate | `/review` |
| Understand a ticket or change in layers, with grounded diagrams | `/walkthrough` |
| Check your own understanding of a change before it reaches production | `/quiz` |
| Stress-test the framing of a problem — root causes, hidden assumptions, trade-offs | `/ask` |
| Build, polish or audit a web interface, ending in a ranked evidence-based report | `/uiux` |

## Project steering

Any repository can keep durable, human-owned context in `.shipmate/steering/*.md` (product
context, tech stack, conventions). `specify`, `run`, `review` and `uiux` read it when present
instead of re-asking — see [`internal/steering.md`](internal/steering.md). Repositories without
steering documents work unchanged.

## Operating at $0

Solo and indie developers shipping on no budget: [`skills/run/references/zero-cost-stack.md`](skills/run/references/zero-cost-stack.md)
collects the free-tier CI, release, hosting and monitoring options `run` can propose
when you ask how to deliver or operate without paid tools.

## Harness Support

| Harness | Slash commands | Adapter source | Notes |
|---|---|---|---|
| Claude Code | ✅ `/specify` `/plan` `/run` `/review` `/walkthrough` `/quiz` `/ask` `/uiux` | marketplace or `--plugin-dir` | validate with `claude plugin validate` |
| Oh-My-Pi / Pi | ✅ all eight | plugin link / `pi install` | commands and skills auto-enabled |
| OpenAI Codex CLI | `$shipmate:*` agent actions | `.codex-plugin/` | manifest-validated |
| OpenCode | eight skills auto-registered | `opencode.mjs`, `.agents/skills/` | add the path to `plugins`, or clone for zero-install |
| Antigravity / Gemini CLI | plugin / extension load | `configs/antigravity-cli/` | validate with `agy plugin validate` |
| Cursor | rules (no slash commands) | `.cursor/rules/`, `.cursorrules` | trigger by intent in chat |
| Windsurf | workflows | `.windsurf/workflows/` | trigger `/specify` etc. in Cascade |
| Continue.dev | prompts | `~/.continue/prompts/` | copy from `.continue/prompts/` |
| GitHub Copilot | instructions | `.github/copilot-instructions.md` | capability routing only |

Every command, rule, workflow and prompt surface is **generated** from `skills/*/SKILL.md` by
`scripts/gen_adapters.py` — edit the skill, then regenerate. `gen_adapters.py --check`,
`stamp_version.py --check` and `scan_secrets.py` run in CI, so hand-edited copies, version
drift and committed credentials fail the build.

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
