# Titanic project: one repository, accessible through the portfolio

The canonical source is [rithmsAI/titanic-ml-project](https://github.com/rithmsAI/titanic-ml-project). The portfolio's `titanic-ml-project` folder is a Git submodule: it points to a specific tested commit in that repository. There is one maintained codebase. The original project history remains in this portfolio.

The separate repository contains the project snapshot extracted from portfolio commit `224b9be3c22832706fea593a1f0d8ece04dfb214`. Original data, model artifacts and tested source files were verified by Git blob hashes during the move.

## New checkout

To download only Titanic:

```powershell
git clone https://github.com/rithmsAI/titanic-ml-project.git
cd titanic-ml-project
```

To keep working from the portfolio:

```powershell
git clone --recurse-submodules https://github.com/rithmsAI/tripleten-portfolio.git
cd tripleten-portfolio
```

Open the portfolio folder in VS Code. Titanic remains inside it. A portfolio ZIP download does not include the submodule's files; use Git or download the standalone repository instead.

## Convert the existing Windows checkout once

Save your VS Code files and finish any running training job. This block requires the portfolio to be on `main` with no modified, staged or untracked files. It creates a timestamped backup, pulls with fast-forward only, preserves ignored leftovers, and initializes the linked project. If it stops, inspect its message before continuing; do not use reset, clean or force-push to bypass the check.

The path checks allow OneDrive cloud placeholders while rejecting symbolic links and junctions. Run this entire block in PowerShell:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $portfolioPath = 'C:\Users\krobi\OneDrive\Documents\GitHub\tripleten-portfolio'
    Set-Location -LiteralPath $portfolioPath
    $branch = git branch --show-current
    if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') {
        throw 'Open the portfolio main branch before continuing.'
    }
    $changes = @(git status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the portfolio.' }
    if ($changes.Count -gt 0) {
        $changes
        throw 'Preserve and review existing changes before migration.'
    }

    $projectPath = Join-Path $portfolioPath 'titanic-ml-project'
    $project = Get-Item -LiteralPath $projectPath
    if ([bool]$project.LinkType -or [bool]$project.Target) {
        throw 'The project is a link or junction; inspect its target first.'
    }
    if (Test-Path -LiteralPath (Join-Path $projectPath '.git')) {
        throw 'The project already has Git metadata; inspect its state first.'
    }
    $backupRoot = Join-Path (Split-Path $portfolioPath -Parent) 'tripleten-portfolio-backups'
    $backupPath = Join-Path $backupRoot ('titanic-before-submodule-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $backupPath | Out-Null
    Copy-Item -LiteralPath $projectPath -Destination (Join-Path $backupPath 'original') -Recurse -Force

    git -c submodule.recurse=false pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) { throw 'Pull stopped. Preserve the backup and inspect the Git message.' }
    $entry = @(git ls-files --stage -- titanic-ml-project)
    if ($LASTEXITCODE -ne 0 -or $entry.Count -ne 1 -or $entry[0] -notmatch '^160000 [0-9a-f]+ 0\t') {
        throw 'Expected submodule entry is missing; inspect before continuing.'
    }

    if (Test-Path -LiteralPath $projectPath) {
        $remaining = @(Get-ChildItem -LiteralPath $projectPath -Force)
        if ($remaining.Count -gt 0) {
            $remainingProject = Get-Item -LiteralPath $projectPath
            if ($remainingProject.FullName -ne $projectPath -or
                [bool]$remainingProject.LinkType -or [bool]$remainingProject.Target -or
                (Test-Path -LiteralPath (Join-Path $projectPath '.git'))) {
                throw 'Unexpected project path; inspect before moving anything.'
            }
            Move-Item -LiteralPath $projectPath -Destination (Join-Path $backupPath 'remaining-local-files')
        }
    }
    git submodule sync --recursive
    if ($LASTEXITCODE -ne 0) { throw 'Submodule synchronization failed.' }
    git submodule update --init --recursive --checkout -- titanic-ml-project
    if ($LASTEXITCODE -ne 0) { throw 'Submodule initialization failed.' }
    git submodule status -- titanic-ml-project
    git -C .\titanic-ml-project remote get-url origin
    git status --short --branch
    Write-Output "Original project backup: $backupPath"
}
```

Verify that the submodule status begins with a space, not `-`, `+` or `U`; its origin is `https://github.com/rithmsAI/titanic-ml-project.git`; and the portfolio is clean. The original files and any ignored leftovers remain in the printed backup folder. This one-time migration block has been reviewed but was not executed against Kaya's local checkout by the assistant.

## Future work

Submodules initially check out the pinned commit in detached HEAD. Before editing, attach Titanic to its branch:

```powershell
git -C .\titanic-ml-project switch main
git -C .\titanic-ml-project pull --ff-only origin main
```

Edit and test the project, then commit and push its changes from inside `titanic-ml-project`. After that, return to the portfolio root and record the updated project pointer:

```powershell
git add -- titanic-ml-project
git commit -m "Update Titanic project"
git push origin main
```

To reproduce the portfolio's recorded version with clean working trees, run `git pull --ff-only` in the portfolio and then `git submodule update --init --recursive`. Avoid `--remote` for reproducible synchronization.

## Docker Hub

The published `rithmsai/titanic-api:1.0` image is still the original submission. The new Docker HEALTHCHECK is verified in CI and available when building from the updated source. Updating GitHub does not rebuild or republish Docker Hub tags automatically.
