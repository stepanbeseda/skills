# Webapp profile — checklist additions

Appended to the project's `checklist.md` during setup when the project is a
web frontend. Same rules as the base checklist: `ok` / `finding` / `n/a`
for every item, an empty line is a blocking finding. The concrete commands
(`npm run build` / `lint` / `test`) come from `project.md` and the spec.

## Build and run

- [ ] The production build is green (strict TypeScript passes, no bare
      `ts-ignore`, no warning that is silently swallowed).
- [ ] The dev server starts from a clean state, runs on the port from the
      config and does not steal a port from another session (`HOST`/`PORT`
      from `.env.example`).
- [ ] The app shows the main flow and the empty states ("you have not added
      anything yet") on a clean data state, not only with a seeded fixture.
- [ ] Data reset/recovery (e.g. `localStorage.clear()`) is described in the
      README and data is never migrated irreversibly without a documented
      way back.
- [ ] Assets (images, icons, fonts) load from the project or a reasonable
      CDN, not from personal paths; no asset is missing (a link to
      `/static/…` that does not exist).

## Env variables and secrets

- [ ] A variable the code reads (`import.meta.env`, `process.env`) has a
      default and an entry in `.env.example`; reading a missing variable
      does not throw during render — it has a sensible fallback.
- [ ] No secret in the client: anything prefixed `VITE_*` / `PUBLIC_*` /
      `NEXT_PUBLIC_*` is published in the bundle and must not contain keys,
      tokens or passwords.
- [ ] `.env*.local`, `node_modules` and the build output are gitignored.

## Data and security

- [ ] Form input is validated before saving and before rendering — no
      `dangerouslySetInnerHTML` / `innerHTML` with user data (XSS).
- [ ] External API calls handle errors (timeout, non-2xx, network) — the UI
      shows the error and a way back, not a silent failure or an endless
      spinner.

## UI and accessibility (main flow)

- [ ] The main flow of the brief has been walked in the browser (see
      `webapp-preview.md`): loading → empty state → action → save → read
      back → error.
- [ ] Main screens work at mobile width (as far as the brief requires), no
      horizontal scrolling in empty states.
- [ ] Texts and UI language match the brief; no lorem ipsum in the
      delivered state.
- [ ] Interactive elements have visible states (hover/focus/disabled), not
      only the default colour.

## Documentation

- [ ] The README covers: running dev, production build, env variables with
      defaults, tests, deployment/target host, how to roll back and what
      must not be damaged while doing so.
