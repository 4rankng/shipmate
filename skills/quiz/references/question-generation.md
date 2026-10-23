# Generate quiz questions

Used by [quiz](../SKILL.md) when preparing the private answer key. The generation prompt below is
sphinx-ci's upstream English prompt ([source](../../../third_party/sphinx-ci/lib/claude.ts.txt),
MIT), verbatim minus its "respond only with JSON" line: Shipmate keeps the answer key in private
working state instead of receiving it as output. `${numQuestions}` is the count from sizing.

In MR/local-branch mode the input is the MR title, changed files and the diff, plus surrounding
context. In Jira mode, use the same answer-key schema and validation but ground questions in the
settled ticket context described in SKILL.md, not the upstream code-diff-only instructions.

> **System:** You are a code review expert. Analyze the Pull Request diff and generate exactly
> ${numQuestions} multiple-choice questions to test the developer's understanding of their own code.
>
> Exact structure:
>
> ```json
> {
>   "questions": [
>     {
>       "id": 1,
>       "question": "Precise question about the code",
>       "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
>       "correct": 0,
>       "explanation": "Short explanation (1-2 sentences)"
>     }
>   ]
> }
> ```
>
> Mandatory rules:
> - Generate exactly ${numQuestions} questions
> - Questions ONLY about the code in the provided diff (no generic questions)
> - Cover: business logic, error handling, side effects, patterns used, edge cases, potential impacts
> - "correct" is the index (0-3) of the correct answer in "options"
> - Difficulty level: senior developer reviewing their own work
> - Vary types: comprehension, impact analysis, potential bug detection
> - Wrong answers must be plausible (not trivial)

## Example source

sphinx-ci's demo questions ([source](../../../third_party/sphinx-ci/components/DemoQuiz.tsx.txt))
show the wanted shape: a concrete change, a consequence-focused question and a one-sentence
evidence-based explanation. Do not copy their cues: each correct option is the longest, and two
stems state the defect. Never reuse them for a real target.
