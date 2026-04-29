# Security

This repository is intended to contain public skill instructions only.

Do not commit:

- API keys, OAuth tokens, cookies, session files, or password files
- `auth.json`, `env.conf`, `.env`, `session.json`, or equivalent credential state
- local email, chat, calendar, document, or finance data
- decrypted databases, exported chats, media caches, or generated reports
- build output such as `target/`, `dist/`, or local binaries
- `.git/`, `.DS_Store`, or tool cache directories

Before publishing updates, run a secret scan similar to:

```bash
rg -n --hidden -i \
  "(api[_-]?key|token|secret|password|credential|authorization|bearer|github_pat|ghp_|gho_|sk-[A-Za-z0-9]|AKIA|AIza|BEGIN [A-Z ]*PRIVATE KEY|auth\\.json|session\\.json|all_keys|decrypted/)" \
  .
```

Treat matches as blockers unless they are clearly documentation examples or code
that handles secret values without embedding real values.
