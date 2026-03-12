# GitHub Copilot / Assistant Instructions

Purpose
- Help maintainers by providing high-quality, concise code suggestions and PR/commit message guidance.

Behavior guidelines
- Follow the project's existing style and patterns.
- Prefer clarity and minimal, well-tested changes.
- When asked to modify files, include only focused changes with clear commit messages.
- If unsure about a breaking change, propose alternatives and ask before applying.

Coding style preferences
- Use descriptive variable and function names (no single-letter names unless conventional).
- Keep functions small and single-responsibility.
- Add type hints where appropriate in Python code.
- Avoid changing unrelated files or reformatting large sections.

Commit message format (recommended)
We follow a concise, structured commit format inspired by Conventional Commits to make messages informative and machine-readable.

Structure:
```
<type>(<scope>): <short summary>

<body> (optional — wrapped at 72 chars)

<footer> (optional — issue refs, BREAKING CHANGES)
```

Types (choose the best fit):
- `feat`: a new feature
- `fix`: a bug fix
- `docs`: documentation-only changes
- `style`: formatting, missing semicolons, etc. (no code changes)
- `refactor`: code change that neither fixes a bug nor adds a feature
- `perf`: code change that improves performance
- `test`: adding or fixing tests
- `chore`: maintenance tasks (build, deps, tooling)

Guidelines:
- Keep the subject under 50 characters and use present tense.
- Optionally include a `scope` (module or file) to clarify target.
- Body should explain the reasoning and high-level approach (wrap at 72 chars).
- Reference related issues in the footer like `Refs #123` or `Fixes #123`.
- Use `BREAKING CHANGE:` in the footer when an API-breaking change is introduced.

Examples:
- `feat(api): add user search endpoint`
- `fix(auth): handle expired tokens in refresh flow`
- `docs: update README with setup instructions`
- `chore: bump pytest to 7.3.0`

Template for quick commits:
```
chore(<scope>): short summary

More detailed explanation of what changed and why.

Refs #<issue>
```

If you generate commit messages or suggest messages for humans, prefer concise, descriptive subjects and a helpful body explaining the reason for the change.

---

If you'd like, I can also add a `commit-msg` hook or `CONTRIBUTING.md` entry that enforces this format automatically.
