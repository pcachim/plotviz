# Releasing plotviz

This document explains how the automated release pipeline works and how to publish a new version.

---

## How it works

Pushing a version tag to GitHub is the only manual step required. Everything else — building, packaging, and publishing — is handled automatically by GitHub Actions.

The pipeline runs three jobs in sequence:

```
push tag  →  build-macos  ──┐
                              ├──  release (attaches assets to GitHub Release)
             build-windows ──┘
```

**build-macos** runs on a GitHub-hosted macOS (Apple Silicon) virtual machine. It installs `uv`, syncs all dependencies, runs PyInstaller against `plotviz.spec`, signs the `.app` bundle ad-hoc, and packages it into a `.dmg` using `create-dmg`.

**build-windows** runs on a GitHub-hosted Windows virtual machine in parallel with the macOS build. It follows the same steps and produces a `.zip` containing the `plotviz.exe` and its runtime files.

**release** runs on an Ubuntu virtual machine after both builds succeed. It downloads both artifacts from GitHub's artifact storage and creates a GitHub Release with the `.dmg` and `.zip` attached as downloadable assets. Release notes are auto-generated from commits and merged PRs since the previous tag.

---

## Step-by-step: publishing a new release

### 1. Bump the version

Edit the single source of truth for the version number:

```
src/plotviz/config/_version.py
```

Change `__version__` to the new version:

```python
__version__ = "2.7.0"
```

`pyproject.toml` reads this file automatically via hatchling, so no other file needs to change.

### 2. Commit and push

```bash
git add src/plotviz/config/_version.py
git commit -m "chore: bump version to 2.7.0"
git push
```

### 3. Create and push the tag

The tag must start with `v` to trigger the workflow:

```bash
git tag v2.7.0
git push origin v2.7.0
```

That's it. The workflow fires immediately.

### 4. Monitor the build

Go to your repository on GitHub and open the **Actions** tab. You will see a workflow run named after your tag. The macOS and Windows build jobs run in parallel and typically finish in 10–20 minutes.

If either job fails, click into it to read the logs. The most common cause is a missing dependency or a PyInstaller hidden import that needs to be added to `plotviz.spec`.

### 5. Check the release

Once the `release` job completes, go to the **Releases** section of your repository. You will find a new release named **plotviz v2.7.0** with:

- Auto-generated changelog
- `plotviz-2.7.0-macos.dmg` — macOS installer (Apple Silicon)
- `plotviz-2.7.0-windows.zip` — Windows portable build

---

## Pre-releases

Any tag that contains a hyphen is automatically marked as a pre-release on GitHub. For example:

```bash
git tag v2.7.0-beta
git push origin v2.7.0-beta
```

This is useful for testing the pipeline or sharing a preview build without it appearing as the latest stable release.

---

## Workflow file location

```
.github/workflows/release.yml
```

The workflow is triggered exclusively by tag pushes matching `v*`. Regular commits and branch pushes do not trigger it.

---

## Optional: Apple Developer ID notarisation

By default the macOS build is signed ad-hoc (`codesign -s -`). This means the app runs but macOS Gatekeeper will show a warning on first launch on other machines.

To enable full notarisation with an Apple Developer ID certificate, add the following secrets to your GitHub repository (**Settings → Secrets and variables → Actions**):

| Secret | Description |
|---|---|
| `APPLE_CERT_B64` | Base64-encoded `.p12` Developer ID certificate |
| `APPLE_CERT_PASSWORD` | Password for the `.p12` file |
| `APPLE_TEAM_ID` | Your 10-character Apple Team ID |
| `APPLE_ID` | Apple ID email used for notarytool |
| `APPLE_APP_PASSWORD` | App-specific password for notarytool |

Then uncomment the **Import Developer ID certificate**, **Re-sign with Developer ID**, and **Notarise** steps in `.github/workflows/release.yml`.

---

## GitHub Actions free tier limits

| Runner | Free minutes (private repos) | Minute multiplier |
|---|---|---|
| Ubuntu | 2,000 / month | 1× |
| Windows | 2,000 / month | 2× |
| macOS | 2,000 / month | 10× |

Each plotviz release consumes roughly 30–50 macOS minutes and 10–15 Windows minutes. For **public repositories**, GitHub Actions is completely free with no minute limits.

## Remove old release artifacts

GitHub does not automatically delete old release assets, so you may want to periodically clean up old `.dmg` and `.zip` files from the **Releases** page to save storage space.

```bash
git tag -d v1.0              # delete locally
git push origin :refs/tags/v1.0   # delete remotely
```
