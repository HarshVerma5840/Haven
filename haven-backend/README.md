# Haven Backend

This is the FastAPI backend for Haven. It provides a production-oriented foundation with structured logging, configuration management, database connections, and basic health checks.

## Development Setup

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Fill in the necessary values. The application will use safe defaults for development if certain values are omitted, but will fail if required production secrets are missing in a production environment.

### 5. Run Alembic migrations

Initialize the database schema:
```bash
alembic upgrade head
```

### 6. Run the API

```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

### 7. Run tests

```bash
pytest
```
