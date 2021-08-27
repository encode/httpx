if (Test-Path './venv')
{
    $PREFIX="./venv/scripts"
}
else
{
    $PREFIX=""
}

& $PREFIX/mkdocs serve