# Publishing to HACS

Notes and a checklist for getting **Aprilaire (Cloud)** installable via HACS —
first as a *custom repository* (works immediately), then, optionally, into the
**HACS default store** (searchable by everyone).

Repo: `Grygon/HA-Aprilaire-Cloud`  ·  Domain: `aprilaire_cloud`

## How HACS installs work

HACS installs a repo's `custom_components/<domain>/` into the user's
`config/custom_components/`. Two ways to be installable:

1. **Custom repository** — any user pastes the repo URL into HACS → *Custom
   repositories* (category *Integration*). No approval needed; works today.
2. **Default store** — a PR to [`hacs/default`](https://github.com/hacs/default)
   adds this repo so it shows up in HACS search for everyone. Requires the
   validation actions to pass and a published release.

## Repository requirements (both paths)

- [x] Public GitHub repo.
- [x] `custom_components/aprilaire_cloud/` with `manifest.json` containing
      `domain`, `name`, `version`, `documentation`, `issue_tracker`, `codeowners`.
- [x] `hacs.json` in the repo root (`name`, `content_in_root: false`,
      `homeassistant` minimum version).
- [x] A README describing usage.
- [ ] **GitHub repo Description** set (shown in HACS). Suggested:
      *"Home Assistant integration for cloud-only Wi-Fi Aprilaire thermostats
      (e.g. 8920W)."*
- [ ] **GitHub Topics** set (searchability). Suggested: `home-assistant`,
      `hacs`, `homeassistant`, `home-assistant-integration`, `aprilaire`,
      `thermostat`, `hvac`, `climate`.
- [ ] A **published GitHub Release** (a real release, not just a tag). The
      release tag becomes the version HACS offers. Tag `v0.1.0` to match
      `manifest.json` / `CHANGELOG.md`.

## Brand assets (required for the default store)

HACS checks that the integration is registered in
[`home-assistant/brands`](https://github.com/home-assistant/brands). This is a
**separate PR** to that repo, not a file in this repo:

- Add `custom_integrations/aprilaire_cloud/icon.png` — **256×256** (a `@2x`
  512×512 `icon@2x.png` is recommended too).
- Optionally `logo.png` (wider wordmark).
- PNGs must be trimmed of surrounding transparent padding and use a transparent
  background.
- The directory name **must** equal the integration `domain` (`aprilaire_cloud`).

> Use an Aprilaire logo only if you're comfortable with the trademark
> implications, or ship a neutral/original icon. The brands repo just needs a
> valid PNG at the right path.

## Validation (must pass before default-store submission)

Two GitHub Actions run on every push/PR (see `.github/workflows/`):

- **`hacs/action`** with `category: integration` — validates repo structure,
  `hacs.json`, `manifest.json`, brands, etc.
- **`home-assistant/actions/hassfest`** — validates the integration manifest the
  same way HA core does.

The default-store rule is strict: *"this action must pass without any errors or
ignores."*

There's also a **`Tests`** workflow running the pytest suite — not required by
HACS, but good hygiene.

## Submitting to the default store

Once the above is green and a release is published:

1. Fork [`hacs/default`](https://github.com/hacs/default).
2. Add `Grygon/HA-Aprilaire-Cloud` to the **`integration`** file,
   **alphabetically**.
3. Open the PR **from a personal account** (not an org) so maintainers can edit
   it. Only the repo owner / a major contributor may submit.
4. After merge, the repo is picked up on the next scheduled scan.

Not accepted as defaults: repos that alpha/beta-test core integrations or
override a core integration. This is a standalone integration for cloud-only
models the core `aprilaire` integration doesn't cover, so that's fine — but the
naming/domain is deliberately distinct (`aprilaire_cloud`) to avoid clashing.

## Versioning

This project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

- **PATCH** (`0.1.0` → `0.1.1`) — bug fixes, no new behaviour.
- **MINOR** (`0.1.0` → `0.2.0`) — new entities/features, backwards-compatible.
- **MAJOR** (`0.x` → `1.0.0`) — breaking changes (renamed/removed entities,
  changed unique IDs, config-entry migrations). While on `0.x`, breaking changes
  may still land in a MINOR bump, but call them out loudly in the changelog.

Three things must always agree for a release: the `version` in
`manifest.json`, the git tag (`vX.Y.Z`), and the top dated section in
`CHANGELOG.md`. HACS reads the **git tag** as the version it offers users, and
hassfest checks the manifest version, so a mismatch means a broken or confusing
release.

## Release checklist (per version)

1. **Land all the changes** for the release on `main` first (or in a PR that's
   merged). Nothing below should introduce new features.
2. **Bump `version`** in `custom_components/aprilaire_cloud/manifest.json`
   (e.g. `0.1.0` → `0.2.0`).
3. **Update `CHANGELOG.md`:**
   - Rename the `## [Unreleased]` section to `## [X.Y.Z] - YYYY-MM-DD` (today's
     date) and leave a fresh empty `## [Unreleased]` above it.
   - At the bottom, update the link references: point `[Unreleased]` at
     `compare/vX.Y.Z...HEAD` and add a `[X.Y.Z]` link to
     `releases/tag/vX.Y.Z`.
4. **Test locally:** `cd devbox && ./run.sh test` — all green.
5. **Commit and push** the manifest + changelog bump to `main`. Confirm the
   **Validate** (HACS + hassfest) and **Tests** GitHub Actions pass.
6. **Publish the GitHub Release** — a real release, not just a tag; the tag must
   match the manifest:

   ```bash
   # Notes from the changelog section, or --generate-notes for auto notes.
   gh release create vX.Y.Z --target main --title "vX.Y.Z" \
     --notes "$(...)"   # e.g. paste the [X.Y.Z] changelog body
   ```

   Pushing a tag alone is **not** enough — HACS only picks up published Releases.
7. HACS users get the update on their next refresh. Verify with
   `gh release view vX.Y.Z` (`isDraft` / `isPrerelease` should both be `false`).

> Pushing changes under `.github/workflows/` requires a token with the
> `workflow` scope. If a push is rejected for that reason, run
> `gh auth refresh -h github.com -s workflow` once and retry.
