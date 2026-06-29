# NoviScope

NoviScope is an evidence-driven research workflow that turns vague research directions into verified experiments and traceable paper drafts.

## Development

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run API locally:

```bash
uvicorn noviscope.main:app --reload
```
