# Format code with ruff (single quotes)
format:
    uv run ruff format .

# Install dependencies
install:
    uv sync

# Install dev dependencies
install-dev:
    uv sync --dev

# Generate the parser module.
parser:
    uv run generate_parser.py

# Run all tests
test:
    uv run python -m pytest tests/ -v --full-trace
