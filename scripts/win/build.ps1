if (Test-Path './venv')
{
    $PREFIX="./venv/scripts"
}
else
{
    $PREFIX=""
}

& $PREFIX/python setup.py sdist bdist_wheel
& $PREFIX/twine check dist/*
& $PREFIX/mkdocs build
