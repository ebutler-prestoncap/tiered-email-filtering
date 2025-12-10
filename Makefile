.PHONY: help build up down logs restart clean test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker compose build

up: ## Start services in background
	docker compose up -d

up-logs: ## Start services with logs
	docker compose up

down: ## Stop services
	docker compose down

restart: ## Restart services
	docker compose restart

logs: ## View logs
	docker compose logs -f

logs-backend: ## View backend logs
	docker compose logs -f backend

logs-frontend: ## View frontend logs
	docker compose logs -f frontend

shell-backend: ## Access backend shell
	docker compose exec backend /bin/bash

shell-frontend: ## Access frontend shell
	docker compose exec frontend /bin/sh

clean: ## Stop and remove containers, volumes
	docker compose down -v

rebuild: ## Rebuild and restart services
	docker compose up --build -d

prod-build: ## Build production images
	docker compose -f docker-compose.prod.yml build

prod-up: ## Start production services
	docker compose -f docker-compose.prod.yml up -d

prod-down: ## Stop production services
	docker compose -f docker-compose.prod.yml down

status: ## Show service status
	docker compose ps

health: ## Check backend health
	curl -f http://localhost:5000/api/health || echo "Backend not healthy"

