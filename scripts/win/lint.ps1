if (Test-Path './venv')
{
    $PREFIX="./venv/scripts"
}
else
{
    $PREFIX=""
}
$SOURCE_FILES=@("./httpx", "./tests") | Foreach-Object {Resolve-Path $_} | Foreach-Object {Convert-Path $_}

& $PREFIX/autoflake --in-place --recursive $SOURCE_FILES
& $PREFIX/isort --project=httpx $SOURCE_FILES
& $PREFIX/black --target-version=py36 $SOURCE_FILES
