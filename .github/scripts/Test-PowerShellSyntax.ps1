# Parses a PowerShell script without running it and fails on any syntax error (ADR-08 §9, SPEC-02 §10).
# Kept out of the workflow YAML: Semgrep reads every `run:` block as a shell script, and the inline
# PowerShell made its engine fail with "Internal matching error", which stops `grdm-dev scan` with exit 51
# (DEMO-21 run 3).
param([Parameter(Mandatory = $true)][string]$Path)
$errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path -LiteralPath $Path).Path, [ref]$null, [ref]$errors)
foreach ($e in $errors) { Write-Host ("::error::{0}: {1}" -f $e.Extent.StartLineNumber, $e.Message) }
if ($errors.Count -gt 0) { exit 1 }
Write-Host "parsed without errors: $Path"
