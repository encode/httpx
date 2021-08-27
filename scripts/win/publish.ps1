$VERSION_FILE="httpx/__version__.py"

if (Test-Path './venv')
{
    $PREFIX="./venv/scripts"
}
else
{
    $PREFIX=""
}

if (Test-Path 'env:GITHUB_ACTIONS')
{
  git config --local user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git config --local user.name "GitHub Action"

  $VERSION=Select-String -Pattern '\"([0-9][^"]*)' $VERSION_FILE | %{$_.Matches.Groups[1].Value}

  if ("refs/tags/${VERSION}" -neq "${GITHUB_REF}")
  {
    echo "GitHub Ref '${GITHUB_REF}' did not match package version '${VERSION}'"
    exit 1
  }
}

& $PREFIX/twine upload dist/*
& $PREFIX/mkdocs gh-deploy --force
