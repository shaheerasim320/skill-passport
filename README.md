# Skill Passport

Skill Passport performs read-only static analysis of public agent-skill repositories before installation. It never installs or executes a fetched skill.

## Install and run

After the package is published, run it without cloning this repository:

```powershell
pipx run skill-passport check github.com/owner/repository
```

Or install it persistently with `pipx install skill-passport`.

## Optional GitHub token

Skill Passport works without a token, using GitHub's unauthenticated request limit. To receive GitHub's higher authenticated limit, set an optional `GITHUB_TOKEN` user environment variable. Do not pass a token as a command-line argument.

For Windows `pipx` users, search for **Edit environment variables for your account**, add a User variable named `GITHUB_TOKEN`, and open a new terminal. This applies to `pipx run` from any directory without cloning or editing source code.

For a cloned checkout, copy `.env.example` to `.env` and set `GITHUB_TOKEN`. An explicit configuration file is also supported with `SKILL_PASSPORT_ENV_FILE`; it takes precedence over a current-directory `.env`. Existing `GITHUB_TOKEN` environment variables always take precedence over `.env` values.

## Windows setup

The CLI automatically configures UTF-8 input/output at startup. Legacy Windows PowerShell may still lack glyph support for coloured emoji; Windows Terminal or the VS Code integrated terminal provides the most consistent rendering.
