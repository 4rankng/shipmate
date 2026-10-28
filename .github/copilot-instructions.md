# Shipmate GitHub Copilot Instructions

Shipmate is an engineering workflow harness for solo developers (one-person software teams),
providing 7 public capabilities:
1. **Specify**: Formulates verified technical specifications from local requirements. See `skills/specify/SKILL.md`.
2. **Run**: Takes requirements through strict TDD, plan reviews, and candidate reviews into a draft MR. See `skills/run/SKILL.md`.
3. **Review**: Performs multi-persona adversarial review of specs, plans, and code diffs. See `skills/review/SKILL.md`.
4. **Walkthrough**: Layered, diagram-backed explanation of behavior, interactions, and details with checkpoints. See `skills/walkthrough/SKILL.md`.
5. **Quiz**: Diagnostic understanding quiz and report for tickets and merge requests. See `skills/quiz/SKILL.md`.
6. **Ask**: Socratic root-cause and critical-thinking interrogation of code, designs, incidents, and decisions, read-only. See `skills/ask/SKILL.md`.
7. **Uiux**: Builds, polishes and reviews web interfaces across design direction, accessibility, layout, typography, color, motion and interface writing with a ranked evidence-based report. See `skills/uiux/SKILL.md`.

When operating under Shipmate:
- The user is a solo developer and the product owner: every material decision is theirs; independent AI review replaces the teammates they don't have.
- Always preserve documentation integrity and test coverage.
- Write failing tests before implementation (TDD).
- Ground findings and recommendations in verifiable repository evidence.
