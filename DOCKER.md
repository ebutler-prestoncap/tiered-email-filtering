# Docker Deployment Guide

This guide covers deploying the Tiered Email Filtering web app using Docker, which is the recommended approach for local development and production deployment.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (or Docker Compose V2 plugin)

Check your installation:
```bash
docker --version
docker compose version
```

## Quick Start

### Development Mode (Recommended for Local)

1. **Build and start all services:**
```bash
docker compose up --build
```

2. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - Health Check: http://localhost:5000/api/health

3. **Stop the services:**
```bash
docker compose down
```

### Production Mode

```bash
docker compose -f docker-compose.prod.yml up --build
```

Access at http://localhost (port 80)

## Docker Compose Commands

### Start Services
```bash
# Start in background (detached mode)
docker compose up -d

# Start with logs
docker compose up

# Rebuild and start
docker compose up --build
```

### Stop Services
```bash
# Stop services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v
```

### View Logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs backend
docker compose logs frontend

# Follow logs
docker compose logs -f
```

### Execute Commands
```bash
# Run command in backend container
docker compose exec backend python -c "print('Hello')"

# Access shell in backend
docker compose exec backend /bin/bash

# Access shell in frontend
docker compose exec frontend /bin/sh
```

## Development Features

### Hot Reload

Both services support hot reload in development mode:
- **Backend**: Code changes in `backend/` are automatically reflected
- **Frontend**: Code changes in `frontend/` trigger Vite HMR

### Volume Mounts

Development mode mounts:
- `./backend` → `/app` (backend code)
- `./tiered_filter.py` → `/app/../tiered_filter.py` (main filter script)
- `./frontend` → `/app` (frontend code)
- Data directories are persisted on host

## Production Deployment

### Build Production Images

```bash
# Build all services
docker compose -f docker-compose.prod.yml build

# Build specific service
docker compose -f docker-compose.prod.yml build backend
```

### Run Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

### Environment Variables

Create a `.env` file for production:

```env
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=your-secret-key-here
```

Then use:
```bash
docker compose -f docker-compose.prod.yml --env-file .env up
```

## Data Persistence

Data is stored in Docker volumes:
- `backend_data` - SQLite database
- `backend_uploads` - Uploaded files
- `backend_results` - Generated Excel files

In development, these are also mounted to host directories for easy access.

### Backup Data

```bash
# Backup database
docker compose exec backend cp /app/data/app.db /app/data/app.db.backup

# Export volume
docker run --rm -v tiered-email-filtering_backend_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backend_data_backup.tar.gz -C /data .
```

### Restore Data

```bash
# Restore volume
docker run --rm -v tiered-email-filtering_backend_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/backend_data_backup.tar.gz -C /data
```

## Troubleshooting

### Port Already in Use

If ports 3000 or 5000 are already in use:

1. Edit `docker-compose.yml`
2. Change port mappings:
```yaml
ports:
  - "3001:3000"  # Frontend on 3001
  - "5001:5000"  # Backend on 5001
```

### Container Won't Start

1. Check logs:
```bash
docker compose logs backend
docker compose logs frontend
```

2. Rebuild containers:
```bash
docker compose down
docker compose up --build
```

### Database Issues

If database is corrupted:
```bash
# Remove data volume
docker compose down -v

# Restart (creates fresh database)
docker compose up
```

### Frontend Can't Connect to Backend

1. Check backend is running:
```bash
docker compose ps
```

2. Check backend logs:
```bash
docker compose logs backend
```

3. Verify health endpoint:
```bash
curl http://localhost:5000/api/health
```

### Clear Everything and Start Fresh

```bash
# Stop and remove everything
docker compose down -v

# Remove images
docker compose rm -f

# Rebuild from scratch
docker compose up --build
```

## Best Practices

### Development

1. **Use docker compose** for local development
2. **Mount volumes** for hot reload
3. **Check logs** regularly: `docker compose logs -f`
4. **Rebuild** when dependencies change: `docker compose up --build`

### Production

1. **Use production compose file**: `docker-compose.prod.yml`
2. **Set environment variables** securely
3. **Use secrets management** (Docker secrets, env files, etc.)
4. **Regular backups** of data volumes
5. **Monitor logs**: `docker compose logs -f`
6. **Health checks** are configured automatically

## Architecture

```
┌─────────────────┐
│   Frontend      │  Port 3000 (dev) / 80 (prod)
│   (React/Vite)  │
└────────┬────────┘
         │ HTTP
         │ /api/*
         ▼
┌─────────────────┐
│   Backend       │  Port 5000
│   (Flask API)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   SQLite DB     │  Volume: backend_data
│   + Files       │
└─────────────────┘
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Flask Deployment](https://flask.palletsprojects.com/en/latest/deploying/)
- [Vite Production Build](https://vitejs.dev/guide/build.html)

