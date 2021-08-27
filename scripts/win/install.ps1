param(
    [string][Alias('p')]$PythonExecutable = "python3"
)

$REQUIREMENTS="requirements.txt"
$VENV="venv"

if (Test-Path 'env:GITHUB_ACTIONS')
{
    $PIP="pip"
}
else
{
    & "$PythonExecutable" -m venv "$VENV"
    $PIP=$VENV/scripts/pip
}

& $PIP install -r $REQUIREMENTS
& $PIP install -e .
