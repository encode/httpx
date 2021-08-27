if (Test-Path './venv')
{
    $PREFIX="./venv/scripts"
}
else
{
    $PREFIX=""
}

& $PREFIX/coverage report --show-missing --skip-covered --fail-under=100
