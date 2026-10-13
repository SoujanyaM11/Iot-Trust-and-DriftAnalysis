# SentinelTrust

SentinelTrust is an IoT trust and drift analysis platform that scores device behavior, highlights suspicious activity, and exposes a dashboard plus APIs for device trust monitoring.

This project uses a FastAPI backend, MongoDB persistence, and a React frontend. MongoDB is required: user accounts, device data, baselines, scores/history, SMTP configuration, and notifications are stored there. Docker is optional.

## Features

- User and admin authentication with JWT tokens
- Per-user device registration and baseline training
- Trust scoring from behavioral, policy, history, and recency signals
- Attack simulation and anomaly detection
- Real-time WebSocket updates
- MongoDB-backed persistence for accounts and trust/device data
- SMTP-based alerting for suspicious events

## Tech stack

- Backend: FastAPI, Motor, PyMongo
- Database: MongoDB
- Frontend: React
- Scoring: custom baseline drift and weighted trust rules
- Auth: passlib + python-jose

## Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB 7.x (recommended)
- Optional: Docker + Docker Compose if you prefer to run MongoDB in a container

## Quick start

### 1) Start MongoDB

Install and start MongoDB Community Server locally, or use a MongoDB Atlas connection string. Make sure your MongoDB service is running before starting the API. For a native Windows installation, MongoDB normally runs as the `MongoDB` Windows service.

Docker is optional. If you prefer a container, the repository includes a MongoDB-only Compose setup:

```bash
docker compose up -d mongo
```

This starts MongoDB on:

- Host: `localhost`
- Port: `27017`
- Database: `sentineltrust`

### 2) Configure the MongoDB connection

On Windows PowerShell, copy `.env.example` to `.env` in the project root, then set the connection string for your MongoDB instance:

```env
MONGODB_URI=mongodb://localhost:27017/sentineltrust
MONGODB_DATABASE=sentineltrust
JWT_SECRET_KEY=<paste-a-random-secret-of-at-least-32-characters>
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000
```

```powershell
Copy-Item .env.example .env
# Generate a key, then paste its output into JWT_SECRET_KEY in .env:
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For MongoDB Atlas, use the connection string provided by Atlas, for example `mongodb+srv://<user>:<password>@<cluster>/`. Set the database name separately in `MONGODB_DATABASE`. Do not commit `.env` or real credentials.

The app also reads MongoDB settings from `config/config.yaml` when no environment variables are set. Startup verifies the MongoDB connection and fails with an explicit error if it cannot connect; the app does not silently switch to JSON files.

### 3) Install backend dependencies

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 4) Run the backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 5) Run the frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:3000

## MongoDB data and configuration

The default MongoDB URI is:

```yaml
mongodb:
  uri: "mongodb://localhost:27017"
  database: "sentineltrust"
```

MongoDB is the required database for the application. The API creates its indexes on startup. Accounts use the `users` and `admins` collections; device details, baselines, and score history use `user_states`; alerts/notifications and SMTP configuration use their corresponding collections.

You can override the configured connection with these environment variables:

- `MONGODB_URI`
- `MONGODB_DATABASE`
- `MONGO_URI`
- `MONGO_DATABASE`
- `MONGODB_DB`

## Project structure

```text
.
├── backend/
│   ├── api/
│   │   └── routes/
│   ├── services/
│   ├── auth_utils.py
│   ├── config_loader.py
│   ├── database.py
│   ├── main.py
│   └── user_data/          # Legacy stores are imported into MongoDB on first access
├── config/
│   └── config.yaml
├── frontend/
│   └── src/
├── ml/                    # Experimental training code; models are not used by the API
├── simulator/
├── docker-compose.yml     # Optional MongoDB container
├── .env.example
├── requirements.txt
├── README.md
└── sample_data/
```

## Authentication

Example registration and login calls:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/user \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo User",
    "email": "demo@example.com",
    "phone": "1234567890",
    "password": "Password123!"
  }'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "Password123!",
    "role": "user"
  }'
```

## Trust score model

The trust score is a weighted combination of:

- behavioral stability
- policy compliance
- historical trust
- recent activity

A typical score range is:

- 90–100: trusted
- 70–89: stable
- 50–69: suspicious
- 30–49: high risk
- 0–29: critical


