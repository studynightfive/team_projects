[CmdletBinding()]
param(
    [Parameter()]
    [string]$Repository,

    [Parameter()]
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI is required. Install gh and run gh auth login first."
}

if (-not $Repository) {
    $Repository = gh repo view --json nameWithOwner --jq ".nameWithOwner"
}

if (-not $Repository -or $Repository -notmatch "^[^/]+/[^/]+$") {
    throw "Cannot determine the repository. Pass -Repository owner/name."
}

# Authentication stays in the gh credential store; this script never reads it.
$protection = @{
    required_status_checks = @{
        strict   = $true
        contexts = @("quality")
    }
    enforce_admins = $false
    required_pull_request_reviews = @{
        dismiss_stale_reviews           = $true
        require_code_owner_reviews      = $false
        required_approving_review_count = 1
        require_last_push_approval      = $true
    }
    restrictions                     = $null
    required_linear_history          = $true
    allow_force_pushes               = $false
    allow_deletions                  = $false
    block_creations                  = $false
    required_conversation_resolution = $true
    lock_branch                      = $false
    allow_fork_syncing               = $true
} | ConvertTo-Json -Depth 5 -Compress

$protection |
    gh api --method PUT "repos/$Repository/branches/$Branch/protection" --input -

if ($LASTEXITCODE -ne 0) {
    throw "Branch protection failed. Repository administrator access is required."
}

Write-Output "Protected $Repository branch $Branch."
