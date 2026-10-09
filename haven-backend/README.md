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

### 5. Run Database Migrations & Seed Data

Initialize the PostgreSQL schemas across the Three-Vault databases and seed the initial users:
```bash
python run_migrations.py
python seed.py
```
*Note: If you already ran migrations before the schemas were physically isolated, you can drop the incorrectly duplicated tables using `python run_migrations.py --reset-dev` (development only).*

### 6. Run the API

```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

### 7. Run tests

```bash
pytest
```
