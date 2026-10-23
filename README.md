# ⚓ Shipmate (v4.4.1)

> **Delivers engineering work from Jira or local requirements, with multi-persona reviews, layered walkthroughs, and diagnostic quizzes for tickets and merge requests.**

Shipmate is an all-in-one engineering delivery plugin designed to run portably across modern AI coding harnesses:
- **Anthropic Claude Code** (`claude`)
- **OpenAI Codex CLI** (`codex`)
- **Oh-My-Pi (OMP)** & **Pi Coding Agent** (`omp` / `pi`)
- **OpenCode** & **OpenClaw** (`opencode`)
- **Google Antigravity** & **Gemini CLI** (`gemini` / `agy`)
- **Cursor** (`cursor`)
- **Windsurf** (`windsurf`)
- **Continue.dev** (`continue`)
- **GitHub Copilot** (`copilot`)

---

## ⚡ The Five Public Actions

| Action | Slash Command | Description | Procedure |
|---|---|---|---|
| **Specify** | `/specify` | Turns intent or Jira requirements into an implementation-ready, reviewed engineering contract | [`skills/specify/SKILL.md`](skills/specify/SKILL.md) |
| **Run** | `/run` | Drives end-to-end implementation through strict TDD, plan reviews, and candidate reviews into a draft MR | [`skills/run/SKILL.md`](skills/run/SKILL.md) |
| **Review** | `/review` | Independent multi-persona review challenging specifications, plans, or diffs with evidence-bound findings | [`skills/review/SKILL.md`](skills/review/SKILL.md) |
| **Walkthrough** | `/walkthrough` | Progressive layered explanation of Jira tickets or merge requests (Intent → Architecture → Changes → Verification) | [`skills/walkthrough/SKILL.md`](skills/walkthrough/SKILL.md) |
| **Quiz** | `/quiz` | Diagnostic comprehension quiz with detailed explanations and a screenshot-ready report | [`skills/quiz/SKILL.md`](skills/quiz/SKILL.md) |

---

## 🚀 Installation & Harness Setup

### 1. Anthropic Claude Code
Shipmate provides `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and native slash commands in `commands/`.

**Install from GitHub Marketplace:**
```bash
claude plugin marketplace add 4rankng/shipmate
claude plugin install shipmate@shipmate-marketplace
```
Or in an active Claude session:
```
/plugin install shipmate --marketplace 4rankng/shipmate
```

**Local load:**
```bash
claude --plugin-dir /path/to/shipmate
```

**Validate plugin compliance:**
```bash
claude plugin validate /path/to/shipmate
```

Once loaded, use `/specify`, `/run`, `/review`, `/walkthrough`, or `/quiz` directly in Claude Code.

---

### 2. Oh-My-Pi (OMP) & Pi Coding Agent
Shipmate is packaged as an OMP extension and Pi package with `.omp-plugin/plugin.json` and `package.json` Pi definitions.

**Link into Oh-My-Pi:**
```bash
omp plugin link /path/to/shipmate
```
Or start an ephemeral session:
```bash
omp --plugin-dir /path/to/shipmate
```

**Install into Pi:**
```bash
pi install /path/to/shipmate -l
```

---

### 3. OpenAI Codex CLI
Codex CLI automatically discovers plugins with `.codex-plugin/plugin.json` and agent definitions in `skills/*/agents/openai.yaml`.

**Add via Codex plugin manager:**
```bash
codex plugin add /path/to/shipmate
```

---

### 4. OpenCode & OpenClaw
Shipmate exports the OpenCode v2 plugin contract via `opencode.mjs` and provides `openclaw.plugin.json`.

**Register in `~/.config/opencode/opencode.json`:**
```json
{
  "plugins": [
    "/path/to/shipmate"
  ]
}
```

Skills are automatically registered as `shipmate:specify`, `shipmate:run`, `shipmate:review`, `shipmate:walkthrough`, and `shipmate:quiz`.

---

### 5. Google Antigravity & Gemini CLI
Shipmate includes Antigravity manifests in `configs/antigravity-cli/plugin.json` and `plugin.json`.

**Validate or import:**
```bash
agy plugin validate /path/to/shipmate
```

---

### 6. Cursor
Cursor rules are pre-packaged:
- `.cursorrules` (workspace-level configuration)
- `.cursor/rules/shipmate-specify.mdc`
- `.cursor/rules/shipmate-run.mdc`
- `.cursor/rules/shipmate-review.mdc`
- `.cursor/rules/shipmate-walkthrough.mdc`
- `.cursor/rules/shipmate-quiz.mdc`

Copy or symlink `.cursorrules` and `.cursor/` into your target workspace.

---

### 7. Windsurf / Cascade
Pre-packaged Cascade workflows in `.windsurf/`:
- `.windsurfrules`
- `.windsurf/workflows/specify.md`
- `.windsurf/workflows/run.md`
- `.windsurf/workflows/review.md`
- `.windsurf/workflows/walkthrough.md`
- `.windsurf/workflows/quiz.md`

---

### 8. Continue.dev
Prompt templates configured in `.continue/prompts/`:
- `specify.prompt`, `run.prompt`, `review.prompt`, `walkthrough.prompt`, `quiz.prompt`.

---

## 🛠️ Shipmate CLI

Shipmate bundles a quick diagnostics and configuration utility:

```bash
# Check detected harnesses and readiness
./bin/shipmate.mjs doctor

# List available skills
./bin/shipmate.mjs list

# Automatically configure for all detected harnesses
./bin/shipmate.mjs install all
```

---

## 🧪 Testing & Verification

Shipmate maintains rigorous test contracts across Python and Node.js:

```bash
# Run complete Python test suite (280 tests)
python3 -m unittest discover -s scripts -p "test_*.py"

# Run Node.js client and telemetry contracts
node scripts/sns-clients/test_metadata.mjs

# Scan for credentials or secrets
python3 scripts/scan_secrets.py .
```

---

## 📁 Repository Structure

```
shipmate/
├── .claude-plugin/           # Claude Code manifest & marketplace descriptor
├── .codex-plugin/            # OpenAI Codex CLI manifest
├── .omp-plugin/              # Oh-My-Pi extension manifest
├── .openclaw-plugin/         # OpenClaw descriptor
├── .cursor/rules/            # Cursor MDC rules
├── .cursorrules              # Cursor root configuration
├── .windsurf/workflows/      # Windsurf / Cascade workflows
├── .windsurfrules            # Windsurf root configuration
├── .continue/prompts/        # Continue.dev prompt templates
├── .github/                  # GitHub Copilot instructions
├── bin/                      # CLI tools (shipmate doctor, install)
├── commands/                 # Slash commands (/specify, /run, /review, /walkthrough, /quiz)
├── configs/                  # Harness-specific extra configs
├── internal/                 # Internal delivery procedures (TDD, review, Jira, GitLab)
├── scripts/                  # CLI tools, metrics, validators, secret scanner
├── skills/                   # Public skills (specify, run, review, walkthrough, quiz)
├── third_party/              # Upstream reference implementations & licenses
├── opencode.mjs              # OpenCode v2 plugin adapter
├── index.ts                  # Universal TypeScript entrypoint
├── plugin.json               # Root plugin manifest
├── package.json              # Monorepo metadata & multi-harness exports
└── README.md                 # Complete documentation
```

---

## 📄 License

MIT © GXS Engineering
