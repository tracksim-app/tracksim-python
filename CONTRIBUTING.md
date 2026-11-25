# Contributing

Thanks for helping improve the TrackSim Python client.

## Reporting bugs and requesting features

Open an issue with what you did, what you expected and what happened, plus your Python and
package versions. Never include your API key, webhook secret or map links.

Questions about the TrackSim service itself (not this library) belong in the TrackSim
Discord or support channels.

## Development setup

```bash
git clone https://github.com/tracksim-app/tracksim-python.git
cd tracksim-python
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Checks

Run all of these before opening a pull request; CI runs the same:

```bash
pytest
mypy
ruff check
ruff format --check
```

Tests mock the HTTP session, so they never call the real API and need no API key.

## Pull requests

- Keep each pull request to one change, with tests for new behaviour.
- Follow the [API docs](https://docs.tracksim.app) for endpoint paths and response fields.
- Add an entry under an `Unreleased` heading in `CHANGELOG.md`.
- Public classes and methods need docstrings and full type hints.

## Releasing (maintainers)

1. Update `src/tracksim/_version.py` and move the changelog entries under the new version.
2. Merge to `main`, then create a GitHub release with the tag `vX.Y.Z`.
3. The release workflow builds the package and publishes it to PyPI.
