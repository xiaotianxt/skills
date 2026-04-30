# 1Password CLI Patterns

Use this reference for local `op` CLI tasks. Prefer official command help for exact flags:

```bash
op read --help
op run --help
op inject --help
op item --help
```

## Auth And Accounts

Check the CLI without touching secrets:

```bash
op --version
op whoami
```

If `op whoami` fails, run:

```bash
op signin
```

If the user has multiple accounts, avoid guessing. Use the account explicitly once known:

```bash
op whoami --account <account>
OP_ACCOUNT=<account> op whoami
```

## Secret References

Standard reference:

```text
op://<vault>/<item>/<field>
op://<vault>/<item>/<section>/<field>
```

Common local convention for API Credential items:

```text
op://Private/<title-or-id>/credential
```

Use item IDs when the item title is unstable or ambiguous.

## Prefer `op run`

Use `op run` when the target command accepts environment variables. It resolves secret references for the child process and masks secrets in stdout/stderr by default.

```bash
API_KEY='op://Private/Service API/credential' op run -- ./script-that-reads-env
```

With an env template:

```bash
# .env.op contains references, not plaintext values.
API_KEY=op://Private/Service API/credential
DATABASE_URL=op://Private/App Database/url
```

```bash
op run --env-file .env.op -- npm run dev
```

Do not use `--no-masking` unless the user explicitly asks to display the secret value.

## Use `op inject` For Config Files

Use `op inject` when a config format needs inline substitution.

```yaml
# config.yml.tpl
api_key: "{{ op://Private/Service API/credential }}"
```

```bash
op inject -i config.yml.tpl -o config.yml
```

Delete resolved files once they are no longer needed. Keep template files because they contain references, not secret values.

## Direct `op read`

Use direct reads only for commands that cannot use `op run` or templates. Keep the value inside the pipeline or command invocation, and do not show it in final responses.

```bash
some-cli login --token "$(op read 'op://Private/Service API/credential')"
```

Avoid command shapes that expose secrets through process arguments when the command supports stdin or environment variables.

## Sensitive Outputs

Treat these as secret-bearing output:

- `op read`
- `op item get --reveal`
- `op run --no-masking`
- resolved files from `op inject`
- service account creation output
- one-time passwords, SSH private keys, cookies, and tokens
