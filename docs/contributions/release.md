# Releasing modelkit

## Prepare releasing branch

```bash
git remote add central https://github.com/Cornerstone-OnDemand/modelkit.git
git fetch central main
git switch -C releasing central/main
```

## Bump version

We use `bump2version` to create the commit and tag required for the release
```bash
bump2version patch
```

## Push commit and tag to central

```bash
git push --follow-tags central releasing:main

# Or more concisely if you have configured git with push.default = upstream
git push --follow-tags 
```

## Package and publish new artifact to pypi

```bash
pip wheel --no-deps .
python -m twine upload modelkit-$(git describe --tags | cut -c 2-)-py3-none-any.whl
```