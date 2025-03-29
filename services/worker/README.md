# Worker Service

Worker service for the slow-workers-challenge project. This service processes tasks received from the API service.

## Requirements

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"
```

## Development

```bash
# Run a worker
python -m worker.main

# Run tests
pytest
```

## Project Structure

```
worker/
├── worker/           # Main package
│   ├── __init__.py
│   ├── main.py       # Worker entry point
│   ├── tasks/        # Task definitions and handlers
│   └── utils/        # Utility functions
├── tests/            # Test directory
├── pyproject.toml    # Project configuration
└── README.md         # This file
```
