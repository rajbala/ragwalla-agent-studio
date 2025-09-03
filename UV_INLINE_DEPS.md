# Using UV with Inline Script Dependencies

This project is configured to use `uv` with inline script dependencies, which allows you to specify dependencies directly in your Python scripts without needing a separate `requirements.txt` file.

## Setup

1. Install `uv`:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Run scripts directly with `uv run`:
```bash
uv run script.py
```

## Inline Dependency Format

Add this header to your Python scripts:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "package1==version",
#     "package2",
#     "package3[extras]",
# ]
# ///
```

## Examples

### Simple Script Example
See `example_script.py` for a working example with click, boto3, urllib3, and rich.

Run it with:
```bash
uv run example_script.py --name "Your Name" --count 3
```

### FastAPI Application
The main `app.py` file is configured with all necessary dependencies inline:
```bash
uv run app.py
```

Or to run with uvicorn:
```bash
uv run --python 3.12 -c "import uvicorn; uvicorn.run('app:app', host='0.0.0.0', port=8000, reload=True)"
```

## Benefits

- **No virtual environment management**: uv handles this automatically
- **Reproducible builds**: Dependencies are locked per script
- **Fast installation**: uv caches packages efficiently
- **Portable scripts**: Dependencies travel with the code

## Project Files with Inline Dependencies

- `app.py` - Main FastAPI application
- `models.py` - Pydantic models
- `database.py` - Database service with aiosqlite
- `ai_service.py` - AI service with aiohttp
- `example_script.py` - Example CLI script

## Running the Application

For development:
```bash
# Run the FastAPI app directly
uv run --python 3.12 app.py

# Or use uvicorn with reload
uv run --python 3.12 -c "import uvicorn; uvicorn.run('app:app', host='0.0.0.0', port=8000, reload=True)"
```

## Notes

- Python 3.12+ is recommended for best compatibility
- uv automatically creates isolated environments for each script
- Dependencies are installed on first run and cached for subsequent runs
- The `# /// script` metadata is a PEP 723 standard for inline script metadata