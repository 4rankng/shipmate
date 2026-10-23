# Shipmate GitHub Copilot Instructions

Shipmate is an engineering workflow harness providing 5 public capabilities:
1. **Specify**: Formulates verified technical specifications from Jira or local requirements. See `skills/specify/SKILL.md`.
2. **Run**: Takes requirements through strict TDD, plan reviews, and candidate reviews into a draft MR. See `skills/run/SKILL.md`.
3. **Review**: Performs multi-persona adversarial review of specs, plans, and code diffs. See `skills/review/SKILL.md`.
4. **Walkthrough**: Layered, diagram-backed explanation of behavior, interactions, and details with checkpoints. See `skills/walkthrough/SKILL.md`.
5. **Quiz**: Diagnostic understanding quiz and report for tickets and merge requests. See `skills/quiz/SKILL.md`.

When operating under Shipmate:
- Always preserve documentation integrity and test coverage.
- Write failing tests before implementation (TDD).
- Ground findings and recommendations in verifiable repository evidence.
