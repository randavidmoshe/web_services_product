# Form Discoverer Platform

AI-driven automated testing platform for web applications.

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for agent)
- Node.js 18+ (optional, for local web dev)

### 2. Start System
```bash
# Copy environment file
cp .env.example .env

# Edit .env and add your Claude API key

# Start all services (includes Redis + Celery worker)
docker-compose up

# You'll see:
# - web: http://localhost:3000
# - api-server: http://localhost:8000
# - database: localhost:5432
# - redis: localhost:6379
# - celery-worker: Processing background jobs
```

### 3. Run Agent (separate terminal)
```bash
cd agent
pip install -r requirements.txt
python main.py
```

### 4. Default Super Admin
- Email: admin@formfinder.com
- Password: admin123
- (Change after first login)

## Project Structure
```
form-discoverer-platform/
├── web-app/          # Next.js frontend
├── api-server/       # FastAPI backend
├── agent/            # Desktop agent
├── database/         # SQL schema
└── QUEUING_SYSTEM.md # Queuing documentation
```

## Queuing System (NEW!)

The platform includes Redis + Celery for background job processing:
- **Non-blocking API**: Returns immediately
- **Scalable**: Add more workers as needed
- **Reliable**: Jobs queue and process in order

See QUEUING_SYSTEM.md for complete documentation.

## Integration Points

### Add Your Code Here:
1. `api-server/services/part1/` - Form page discovery logic
2. `api-server/services/part2/` - Form detail analysis logic  
3. `agent/crawler/` - Selenium crawling code

See README files in each directory for details.
