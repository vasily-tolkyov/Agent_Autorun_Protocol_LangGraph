param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ArgsFromCaller
)

$repoRoot = Split-Path -Parent $PSScriptRoot
python (Join-Path $PSScriptRoot "install.py") @ArgsFromCaller
