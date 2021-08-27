if (Test-Path './venv')
{
    $PREFIX="./venv/scripts"
}
else
{
    $PREFIX=""
}
$SOURCE_FILES=@("./httpx", "./tests") | Foreach-Object {Resolve-Path $_} | Foreach-Object {Convert-Path $_}

& $PREFIX/black --check --diff --target-version=py36 $SOURCE_FILES
& $PREFIX/flake8 $SOURCE_FILES
& $PREFIX/mypy $SOURCE_FILES
& $PREFIX/isort --check --diff --project=httpx $SOURCE_FILES