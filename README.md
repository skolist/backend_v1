## Development Setup

Install dependencies and set up pre-commit hooks:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

To run linting manually:

```bash
ruff check .        # lint
ruff format .       # format
pre-commit run --all-files  # run all hooks
```
## License
Apache License 2.0

“Skolist” is a trademark of Skolist Tech.
