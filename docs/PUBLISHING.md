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

## Release checklist (per version)

1. Bump `version` in `manifest.json`.
2. Move items from **Unreleased** to a new dated section in `CHANGELOG.md`.
3. Commit, push, confirm **Validate** + **Tests** actions are green.
4. Create a GitHub Release with tag `vX.Y.Z` (matching the manifest).
5. HACS users get the update on the next refresh.
