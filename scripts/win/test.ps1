if (Test-Path './venv')
{
    $PREFIX="./venv/scripts"
}
else
{
    $PREFIX=""
}


if (!(Test-Path 'env:GITHUB_ACTIONS'))
{
    & scripts/win/check.ps1
}

& $PREFIX/coverage run -m pytest "$args"

if (!(Test-Path 'env:GITHUB_ACTIONS'))
{
    & scripts/win/coverage.ps1
}
