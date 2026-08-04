# Gyme FastAPI: Agent Instructions

## Commands (Exact)

### Setup
```bash
# Python
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate   # Windows
pip install -r app/requirements.txt

# Node (for Tailwind)
npm install
```

### Dev
```bash
# Start FastAPI (uvicorn)
uvicorn app.main:app --reload

# Start Tailwind watcher (parallel terminal)
npm run css:watch
```

### Build
```bash
# Build Tailwind CSS (minified)
npm run css:build
```

### Test
```bash
# No explicit test command found. Use:
pytest  # If tests exist
```

### Lint/Format
```bash
# Ruff (lint)
ruff check .

# Black (format)
black .
```

## Architecture

### Stack
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Templates**: Jinja2 (with custom Jalali date filters)
- **DB**: PocketBase (via SDK)

### Key Directories
```
app/
├── routes/       # FastAPI routers (feature-organized)
├── services/     # Business logic (empty placeholder)
├── static/       # CSS, JS, images
├── templates/    # Jinja2 templates
├── main.py       # FastAPI app setup
├── middleware.py # TenantMiddleware
└── templates.py  # Jinja2 env + Jalali filters
```

### Entry Points
- **FastAPI**: `app.main:app`
- **Templates**: `app/templates.py` (Jinja2 env + Jalali date filters)
- **Static**: `app/static/css/input.css` (Tailwind input)

### Quirks
- **Jalali Dates**: Custom Jinja2 filters (`jalali_year`, `jalali_date`) in `templates.py`.
- **Swagger**: Disabled in production (`IS_PROD` env var).
- **Tenant Middleware**: Applied globally via `TenantMiddleware`.
- **Tailwind**: Outputs to `app/static/css/app.css` (minified for prod).

## Constraints
- **Python**: 3.11+ (per `pyproject.toml`).
- **Node**: Required for Tailwind CSS.
- **Env Vars**: `ENV=production` disables Swagger/docs.
- **PocketBase**: Must be running (version ≥0.17.1).

## Workflow Order
1. **Setup**: Python venv + Node deps.
2. **Dev**: Run `uvicorn` + `npm run css:watch` in parallel.
3. **Build**: `npm run css:build` before deployment.
4. **Lint**: `ruff check .` + `black .` (order irrelevant).

## Gotchas
- **Tailwind Input**: Must watch `input.css` → outputs to same file (dev) or `app.css` (prod).
- **Jinja2 Filters**: Must be registered before template rendering.
- **PocketBase**: No local mock → must be running for full functionality.

## References
- `pyproject.toml`: Ruff/Black config.
- `package.json`: Tailwind scripts.
- `app/requirements.txt`: Python deps.
- `app/templates.py`: Jalali date filters.