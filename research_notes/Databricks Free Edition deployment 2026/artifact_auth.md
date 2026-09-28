# GitHub package handoff and attended Databricks upload

Research checked 2026-09-26. Databricks source pages below generally say “Last updated Sep 11, 2026”; the CLI command index says Sep 24, 2026. GitHub Docs and CLI manual pages cited below did not display a publication or last-updated date in the fetched content and were checked on 2026-09-26.

## How can CI produce and the admin retrieve the exact tested package?

### Takeaway
The existing release workflow already creates a per-commit Actions artifact containing the flat `build/dev/release` package. An admin can select a run by its ID and SHA, download that named artifact, and verify its manifest; tag releases instead contain the individual package files. The current tag `publish` job needs a dependency setup fix before its Release assets can be relied on.

### Cited Findings
- The local `release.yml` is triggered by pushes to `master` and `v*` tags, builds `uv run mdf package --env dev --release`, verifies it, runs pytest, and uploads `build/dev/release` as `mdf-release-${{ github.sha }}` with 30-day retention. The separate `publish` job is tag-only and attaches `build/dev/release/*` as individual GitHub Release assets. — [Local release workflow](../../.github/workflows/release.yml)
- The local `publish` job calls `uv run mdf verify-package build/dev/release` after checkout and download, but has no `astral-sh/setup-uv` or `uv sync --locked` step. Unlike the preceding job, it cannot assume `uv` or the project environment exists on its fresh runner. This is a workflow gap; add setup-uv and locked sync before verification. — [Local release workflow](../../.github/workflows/release.yml); [GitHub job runner model](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idruns-on)
- `src/mdf/package.py` writes `manifest.json` with each generated file’s SHA-256 and `verify_package` recomputes all listed hashes and rejects missing or extra top-level files. The verifier does not authenticate the manifest itself, and `file_count` is returned but not checked against `files` length. — [Local package implementation](../../src/mdf/package.py)
- GitHub’s `upload-artifact`/`download-artifact` pair stores build output; v4 artifacts are immutable within a run. Upload returns a SHA-256 artifact digest; the download action automatically checks it and warns on mismatch. This action digest covers the GitHub artifact, not the package manifest’s source identity. — [GitHub artifact tutorial](https://docs.github.com/en/actions/tutorials/store-and-share-data); [GitHub upload-artifact action](https://github.com/actions/upload-artifact)
- A signed-in person with repository read access can download a run artifact from the Actions run page; `gh run download RUN_ID -n ARTIFACT_NAME -D DIR -R OWNER/REPO` is the CLI equivalent. With one artifact selected, files extract directly into the target directory. The run ID pins a run; the artifact is still subject to expiry or deletion. — [GitHub download docs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts); [GitHub CLI run download](https://cli.github.com/manual/gh_run_download)
- `gh run view RUN_ID --json headSha,conclusion,status` exposes the selected run’s commit and result; `gh run list --commit SHA --workflow release.yml` can locate runs. `gh auth login --web` starts the human GitHub sign-in. — [GitHub CLI run view](https://cli.github.com/manual/gh_run_view); [GitHub CLI run list](https://cli.github.com/manual/gh_run_list); [GitHub CLI auth login](https://cli.github.com/manual/gh_auth_login)
- `gh release download TAG -D DIR -R OWNER/REPO` downloads all attached release assets for a specific tag. In this repository those assets are the individual manifest and resolved files, while GitHub’s automatic source ZIP/tarball represents repository source, not this built package. Each Release asset must be under 2 GiB. — [GitHub CLI release download](https://cli.github.com/manual/gh_release_download); [GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases); [Local release workflow](../../.github/workflows/release.yml)
- The repository's PR CI publishes a distinct `mdf-preview-${{ github.run_id }}` artifact with 7-day retention. It is not the gated release package. — [Local PR CI workflow](../../.github/workflows/ci.yml)

Copyable PowerShell for the **run artifact**, assuming GitHub CLI is installed and the administrator is at a checkout of the same commit with `uv` installed:

```powershell
$repo = 'franceZa/MetadataRegistry'
$runId = '<successful-release-run-id>'
gh auth login --web
$run = gh run view $runId -R $repo --json headSha,conclusion,status | ConvertFrom-Json
if ($run.conclusion -ne 'success') { throw "Run $runId did not succeed" }
$sha = $run.headSha
$pkg = Join-Path (Get-Location) "downloads/$sha"
New-Item -ItemType Directory -Force -Path $pkg | Out-Null
gh run download $runId -R $repo -n "mdf-release-$sha" -D $pkg
if ($LASTEXITCODE -ne 0) { throw 'Artifact download failed' }
git checkout --detach $sha
uv sync --locked
uv run mdf verify-package $pkg
if ($LASTEXITCODE -ne 0) { throw 'Package verification failed' }
Get-FileHash (Join-Path $pkg 'manifest.json') -Algorithm SHA256
```

The run selector, extraction behavior, and manifest check in that example are supported by [GitHub CLI run view](https://cli.github.com/manual/gh_run_view), [GitHub CLI run download](https://cli.github.com/manual/gh_run_download), and the [local verifier](../../src/mdf/package.py). The last hash line is useful for an audit log but is not independent provenance of the manifest.

For a **published tag release** after the `publish` job is fixed, replace the download part with:

```powershell
$tag = 'v1.2.3' # replace with the approved tag
$pkg = Join-Path (Get-Location) "downloads/$tag"
New-Item -ItemType Directory -Force -Path $pkg | Out-Null
gh release download $tag -R 'franceZa/MetadataRegistry' -D $pkg
if ($LASTEXITCODE -ne 0) { throw 'Release download failed' }
uv run mdf verify-package $pkg
if ($LASTEXITCODE -ne 0) { throw 'Package verification failed' }
```

`gh release download` is documented by the [GitHub CLI manual](https://cli.github.com/manual/gh_release_download); the package verification command is the [local CLI](../../src/mdf/cli.py). Run the verifier from a checkout of the tag or equivalent installed project environment.

### Inferences
- Record `(repository, run ID, head SHA, artifact name, manifest SHA-256, administrator, deployment destination)` in the approval record. The SHA in the artifact name is a convenient cross-check, while the run ID and successful conclusion identify the tested Actions execution. — Inference from [GitHub CLI run metadata](https://cli.github.com/manual/gh_run_view) and [local release workflow](../../.github/workflows/release.yml).
- Since `upload-artifact@v4` includes the contents of the specified directory and the run download extracts one artifact into its target directory, the admin should point `mdf verify-package` at that extracted directory, not at a `release.zip` or an extra `release` subfolder. — Inference from [GitHub artifact tutorial](https://docs.github.com/en/actions/tutorials/store-and-share-data) and [local release workflow](../../.github/workflows/release.yml).

### Gaps
- No successful live run or published Release was inspected; the local workflow’s tag job gap means Release assets should not be assumed to exist until the job is repaired and a successful run is observed.
- Official sources reviewed did not establish a single general maximum size for a GitHub Actions artifact. The relevant documented constraints here are retention/storage quota and the 2 GiB limit per GitHub Release asset.

## How should the package’s integrity and provenance be checked?

### Takeaway
The local manifest catches changed, missing, and extra payload files after download, but it cannot prove who produced the manifest. For a strong trust anchor, use GitHub’s signed artifact attestation or an immutable GitHub Release with its signed release attestation, subject to repository eligibility and configuration.

### Cited Findings
- GitHub artifact attestations require `id-token: write`, `contents: read`, and `attestations: write` plus `actions/attest@v4` with `subject-path` for binaries/files. GitHub Free, Pro, and Team support attestations for public repositories; private/internal repositories require GitHub Enterprise Cloud. — [GitHub attestation guide](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- `gh attestation verify FILE --repo OWNER/REPO` verifies a signed attestation against a local file and the repository identity; the CLI supports `--signer-workflow` and `--source-digest` for stronger expected-identity checks. An attestation has to be generated in CI first. The current local release workflow has no attestation step or permissions. — [GitHub CLI attestation verify](https://cli.github.com/manual/gh_attestation_verify); [Local release workflow](../../.github/workflows/release.yml)
- GitHub's release immutability setting locks a published release’s assets and tag and creates a cryptographically verifiable release attestation. It is a repository setting, not implied merely by using `gh release create`. A draft can hold assets before publication. — [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases); [GitHub CLI release create](https://cli.github.com/manual/gh_release_create)
- For an immutable release, `gh release verify TAG` checks the release attestation and `gh release verify-asset TAG FILE` checks a downloaded local asset against the release attestation. `gh release view TAG --json isImmutable` exposes its immutable status. — [GitHub CLI release verify-asset](https://cli.github.com/manual/gh_release_verify-asset); [GitHub CLI release view](https://cli.github.com/manual/gh_release_view); [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- GitHub Release assets can otherwise be edited or deleted by writers; enabling immutable releases prevents modifications after publication. Thus `mdf verify-package` alone cannot prove that a malicious replacement manifest and matching payload were not substituted into a mutable release. — [GitHub release management](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository); [Local package implementation](../../src/mdf/package.py)

If repository **release immutability is enabled**, check all downloaded Release assets and the package:

```powershell
$repo = 'franceZa/MetadataRegistry'
$tag = 'v1.2.3'
$pkg = Join-Path (Get-Location) "downloads/$tag"
$release = gh release view $tag -R $repo --json isImmutable | ConvertFrom-Json
if (-not $release.isImmutable) { throw 'Release is not immutable' }
gh release verify $tag -R $repo
if ($LASTEXITCODE -ne 0) { throw 'Release attestation failed' }
Get-ChildItem -LiteralPath $pkg -File | ForEach-Object {
    gh release verify-asset $tag $_.FullName -R $repo
    if ($LASTEXITCODE -ne 0) { throw "Release asset verification failed: $($_.Name)" }
}
uv run mdf verify-package $pkg
if ($LASTEXITCODE -ne 0) { throw 'Package manifest verification failed' }
```

These command forms are documented in the [GitHub CLI release verify manual](https://cli.github.com/manual/gh_release_verify), [release asset verify manual](https://cli.github.com/manual/gh_release_verify-asset), and [local verifier](../../src/mdf/package.py). An alternative future CI addition is to attest an archive or each released file with `actions/attest@v4`, then run `gh attestation verify` for each downloaded file; do not claim this works for current runs until the workflow actually emits those attestations. — [GitHub attestation guide](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations); [GitHub CLI attestation verify](https://cli.github.com/manual/gh_attestation_verify)

### Inferences
- The strongest current path, once fixed and configured, is: successful tag run → individual Release assets → immutable-release signed attestation → local manifest verifier → attended upload. The run artifact remains useful for testing and recovery during its 30-day retention window. — Inference from [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases), [GitHub CLI release verify-asset](https://cli.github.com/manual/gh_release_verify-asset), and [local workflow](../../.github/workflows/release.yml).
- For immutable release publishing, keep the current `gh release create TAG ...files` pattern because the GitHub CLI creates a draft, uploads the assets, then publishes when immutability is enabled. — Inference from [GitHub CLI release create](https://cli.github.com/manual/gh_release_create).

### Gaps
- The repository’s GitHub Release immutability setting and plan eligibility for artifact attestations were not inspected. Treat all signed verification commands as conditional until those facts are checked.
- GitHub’s Actions artifact digest is reported by the upload and checked by `actions/download-artifact` during a workflow; official sources reviewed do not document the same automatic digest check for the admin’s `gh run download` command. The package manifest verifier remains necessary for that path.

## How does an administrator authenticate and upload to a Volume or workspace folder?

### Takeaway
The admin can use attended OAuth U2M from a local Databricks CLI profile, then copy the verified files to either a governed Unity Catalog Volume or a workspace folder. Use `databricks fs` with `dbfs:/Volumes/...` for a Volume, and `databricks workspace` with `/Workspace/...` for workspace files.

### Cited Findings
- Databricks CLI 0.205+ is supported; on Windows, official instructions use `winget install Databricks.DatabricksCLI`, then `databricks -v`. The cited install page says last updated Sep 11, 2026. — [Databricks CLI install](https://docs.databricks.com/aws/en/dev-tools/cli/install)
- `databricks auth login --host <workspace-url>` starts browser-based OAuth U2M and saves a profile; `databricks auth profiles` lists profiles, `-p PROFILE` selects one, and `databricks current-user me` identifies the authenticated user. This is the attended user flow; unattended CI generally uses another method, but this handoff does not require Databricks credentials in GitHub. The auth pages say last updated Sep 11, 2026. — [Databricks CLI authentication](https://docs.databricks.com/aws/en/dev-tools/cli/authentication); [Databricks auth commands](https://docs.databricks.com/aws/en/dev-tools/cli/reference/auth-commands); [Databricks auth method overview](https://docs.databricks.com/aws/en/dev-tools/auth/)
- Modern CLI U2M tokens are stored by default in OS-native secure storage, including Windows Credential Manager, while `.databrickscfg` holds non-secret host/profile settings. OAuth access tokens are short-lived and automatically refreshed by supported tools. — [Databricks CLI authentication](https://docs.databricks.com/aws/en/dev-tools/cli/authentication); [Databricks OAuth U2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m)
- A Unity Catalog Volume upload needs a UC-enabled workspace plus `USE CATALOG`, `USE SCHEMA`, and `WRITE VOLUME` on the destination; Databricks’ volume privilege table also lists `READ VOLUME` for create/update file operations. Volumes are recommended for non-tabular data and build artifacts. The pages say last updated Sep 11, 2026. — [Databricks volume file operations](https://docs.databricks.com/aws/en/volumes/volume-files); [Databricks volume privileges](https://docs.databricks.com/aws/en/volumes/privileges)
- `databricks fs cp SOURCE TARGET -r` recursively copies a local directory to a Volume; Volume paths passed to the CLI must begin `dbfs:/Volumes`. `databricks fs ls` lists the uploaded folder. The `fs` commands are for Volumes/DBFS, not `/Workspace` files. The CLI reference says last updated Sep 11, 2026. — [Databricks fs command reference](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands)
- Workspace files accept code, YAML, JSON, and other files but each workspace file has a 500 MB limit. `databricks workspace mkdirs PATH`, `workspace import TARGET --file LOCAL --format RAW`, and `workspace list PATH` are the appropriate CLI operations. `workspace import-dir` recursively imports a directory but strips notebook extensions, which can alter package filenames; importing each package file as RAW gives explicit names. The workspace command reference says last updated Sep 11, 2026. — [Databricks workspace files](https://docs.databricks.com/aws/en/files/workspace); [Databricks workspace command reference](https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands)
- Volume files can be as large as the underlying cloud storage permits; the Databricks UI has a 5 GB upload limit and recommends the Python SDK above it. This is a UI limit, not a documented CLI limit. — [Databricks volume file operations](https://docs.databricks.com/aws/en/volumes/volume-files)
- Volume paths inside Databricks code use `/Volumes/catalog/schema/volume/...`, whereas the CLI form is `dbfs:/Volumes/catalog/schema/volume/...`; workspace code uses `/Workspace/...`, and `databricks workspace` commands use the workspace object path. — [Databricks volume file operations](https://docs.databricks.com/aws/en/volumes/volume-files); [Databricks fs command reference](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands); [Databricks workspace command reference](https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands)

PowerShell, after the verified `$pkg` and `$sha` from the first snippet exist:

```powershell
winget install Databricks.DatabricksCLI
databricks -v
databricks auth login --host 'https://<your-workspace-host>'
databricks auth profiles
$profile = '<profile-name-chosen-during-login>'
databricks current-user me -p $profile

# Choose one destination. Volume example:
$volumeDest = "dbfs:/Volumes/<catalog>/<schema>/<volume>/mdf/releases/$sha"
databricks fs mkdir $volumeDest -p $profile
Get-ChildItem -LiteralPath $pkg -File | ForEach-Object {
    $target = "$volumeDest/$($_.Name)"
    databricks fs cp $_.FullName $target -p $profile
    if ($LASTEXITCODE -ne 0) { throw "Volume upload failed: $($_.Name)" }
}
databricks fs ls $volumeDest -p $profile

# Workspace-folder alternative; keep each filename as RAW:
$workspaceDest = "/Workspace/Shared/mdf/releases/$sha"
databricks workspace mkdirs $workspaceDest -p $profile
Get-ChildItem -LiteralPath $pkg -File | ForEach-Object {
    $target = "$workspaceDest/$($_.Name)"
    databricks workspace import $target --file $_.FullName --format RAW -p $profile
    if ($LASTEXITCODE -ne 0) { throw "Workspace import failed: $($_.Name)" }
}
databricks workspace list $workspaceDest -p $profile
```

CLI syntax and path forms in that example come from [Databricks CLI authentication](https://docs.databricks.com/aws/en/dev-tools/cli/authentication), [fs commands](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands), and [workspace commands](https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands). The `$sha` suffix is an inferred practical convention for avoiding overwrites and recording which approved build was uploaded.

### Inferences
- Prefer a Volume for the release package when the Free Edition workspace exposes Unity Catalog Volumes and the admin has the privileges, because Databricks specifically lists build artifacts among volume uses and Volume paths keep non-tabular files under UC governance. Workspace files remain a workable fallback for small package files and code. — Inference from [Databricks volume file operations](https://docs.databricks.com/aws/en/volumes/volume-files) and [Databricks file recommendations](https://docs.databricks.com/aws/en/files/files-recommendations).
- Upload into a new SHA-named destination and avoid `--overwrite` for the first upload. This makes the human-approved deployment target easier to audit and avoids silently replacing a prior package. — Inference from [Databricks fs `--overwrite` behavior](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands), [workspace import `--overwrite` behavior](https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands), and the [local SHA-named artifact](../../.github/workflows/release.yml).

### Gaps
- No live Databricks Free Edition workspace was available to confirm its workspace host, target catalog/schema/volume, effective grants, or whether workspace import behavior matches these commands in that tenant.
- Databricks docs cited here state the 5 GB UI Volume limit and 500 MB workspace-file limit, but no distinct maximum for `databricks fs cp` to a Volume was found. Do not apply the UI’s 5 GB cap to CLI uploads without further evidence.
