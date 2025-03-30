# Slow Workers Challenge

A monorepo project containing a HTTP API and worker services for processing slow tasks.

## Requirements

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

## Project Structure

The project is organized into two main services:

- **API Service** (`services/api`): HTTP API to receive requests and pass them to the workers cluster
- **Worker Service** (`services/worker`): Service for processing slow tasks

## Development Setup

Both services use [uv](https://github.com/astral-sh/uv) for dependency management and [ruff](https://github.com/astral-sh/ruff) for linting.

### API Service Setup

```bash
cd services/api
uv pip install -e .
uv pip install -e ".[dev]"

# Run the service
uvicorn api.main:api --reload
```

### Worker Service Setup

```bash
cd services/worker
uv pip install -e .
uv pip install -e ".[dev]"

# Run a worker instance
python -m worker.main
```

## Documentation

See individual service directories for detailed documentation on each service:

- [API Service](services/api/README.md)
- [Worker Service](services/worker/README.md)
