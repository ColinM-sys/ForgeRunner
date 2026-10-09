# ForgeRunner

Unified Training Data Quality Dashboard for AI/ML pipelines. Upload, score, review, and export training datasets with automated quality analysis powered by Cleanlab, sentence embeddings, and source verification.

## Features

- **Dataset Upload & Ingestion** — Upload JSONL training data files (up to 200MB) with automatic parsing and storage
- **Automated Quality Scoring** — Multi-engine scoring pipeline that evaluates every training example:
  - **Cleanlab Engine** — Detects label errors, data issues, and confidence scores
  - **Forge Embedder Engine** — Generates sentence embeddings (all-MiniLM-L6-v2) for similarity analysis and duplicate detection
  - **Source Checker Engine** — Verifies data provenance and source integrity
- **Review Queue** — Human-in-the-loop review interface for flagged examples — approve, reject, or re-bucket training data
- **Smart Bucketing** — Automatically categorize examples into quality buckets with customizable thresholds
- **Source Tracking** — Track where training data originated and monitor source quality over time
- **Dataset Estimator** — Estimate dataset quality metrics and coverage before committing to a full training run
- **Export** — Export cleaned, reviewed datasets ready for fine-tuning in multiple formats
- **Dashboard** — Real-time overview of dataset health, scoring progress, and quality distributions

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI (Python), async |
| Database | SQLite (async via aiosqlite), SQLAlchemy, Alembic |
| ML/Scoring | Cleanlab, Sentence-Transformers, BERTopic, scikit-learn, PyTorch |
| Embeddings | all-MiniLM-L6-v2 (runs on CUDA) |

## Quick Start

### Backend

```bash
# Install dependencies
pip install -e .

# Copy environment config
cp .env.example .env

# Create data directories
mkdir -p data/uploads data/exports data/embeddings

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `/api/datasets` | Dataset CRUD operations |
| `/api/examples` | Browse and manage training examples |
| `/api/scoring` | Trigger and monitor quality scoring |
| `/api/buckets` | Manage quality buckets and thresholds |
| `/api/review` | Human review queue for flagged examples |
| `/api/export` | Export cleaned datasets |
| `/api/dashboard` | Dashboard stats and metrics |
| `/api/sources` | Source tracking and analysis |
| `/api/estimator` | Dataset quality estimation |

## Architecture

```
Upload JSONL > Ingest & Parse > Multi-Engine Scoring > Bucketing > Review Queue > Export
                                      |
                          +-----------+-----------+
                          |           |           |
                     Cleanlab    Embedder    Source Check
                   (label QA)  (similarity)  (provenance)
```

## Requirements

- Python 3.10+
- Node.js 18+
- CUDA-capable GPU (for embeddings and scoring)


---

## Author

Built by **Colin McDonough** — [LinkedIn](https://www.linkedin.com/in/colinmcdonoughmarketing) · [GitHub](https://github.com/ColinM-sys)
