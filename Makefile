# Face Recognition Attendance System Makefile
# Convenient commands for development and deployment

.PHONY: help build start stop restart logs clean dev test deploy health backup

# Default target
help:
	@echo "Face Recognition Attendance System"
	@echo "=================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make start     - Start the system (build if needed)"
	@echo "  make stop      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make build     - Build Docker images"
	@echo "  make logs      - View live logs"
	@echo "  make clean     - Remove containers and volumes"
	@echo "  make dev       - Start in development mode"
	@echo "  make test      - Run tests"
	@echo "  make deploy    - Production deployment"
	@echo "  make health    - Check system health"
	@echo "  make backup    - Create system backup"
	@echo "  make setup     - Initial setup and configuration"
	@echo ""

# Setup and configuration
setup:
	@echo "🔧 Setting up Face Recognition Attendance System..."
	@mkdir -p data uploads face_templates logs exports backups
	@if [ ! -f .env ]; then \
		echo "Creating .env file..."; \
		echo "FLASK_ENV=production" > .env; \
		echo "SECRET_KEY=$$(openssl rand -hex 32)" >> .env; \
		echo "DATABASE_URL=sqlite:///data/attendance.db" >> .env; \
		echo "FACE_RECOGNITION_MODEL=GhostFaceNet" >> .env; \
		echo "ANTI_SPOOFING_ENABLED=true" >> .env; \
		echo "MAX_UPLOAD_SIZE=16777216" >> .env; \
	fi
	@echo "✅ Setup complete!"

# Build Docker images
build:
	@echo "🔨 Building Docker images..."
	@docker-compose build

# Start the system
start: setup
	@echo "🚀 Starting Face Recognition Attendance System..."
	@docker-compose up -d
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo ""
	@echo "✅ System started successfully!"
	@echo "🌐 Web Interface: http://localhost:5000"
	@echo "🗄️  Database Admin: http://localhost:8080"
	@echo "💓 Health Check: http://localhost:5000/health"

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	@docker-compose down
	@echo "✅ All services stopped."

# Restart services
restart:
	@echo "🔄 Restarting services..."
	@docker-compose restart
	@echo "✅ Services restarted."

# View logs
logs:
	@echo "📋 Viewing live logs (Ctrl+C to exit)..."
	@docker-compose logs -f

# Development mode
dev: setup
	@echo "🧪 Starting in development mode..."
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Run tests
test:
	@echo "🧪 Running tests..."
	@docker-compose exec face-recognition-app python -m pytest tests/ -v

# Production deployment
deploy: setup build
	@echo "🚀 Production deployment..."
	@docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "✅ Production deployment complete!"

# Health check
health:
	@echo "💓 Checking system health..."
	@curl -s http://localhost:5000/health | python -m json.tool || echo "❌ Health check failed"

# Backup system
backup:
	@echo "💾 Creating system backup..."
	@mkdir -p backups
	@DATE=$$(date +%Y%m%d_%H%M%S); \
	if [ -f data/attendance.db ]; then \
		cp data/attendance.db backups/attendance_$$DATE.db; \
		echo "✅ Database backup: backups/attendance_$$DATE.db"; \
	fi
	@DATE=$$(date +%Y%m%d_%H%M%S); \
	if [ -d face_templates ]; then \
		tar -czf backups/face_templates_$$DATE.tar.gz face_templates/; \
		echo "✅ Face templates backup: backups/face_templates_$$DATE.tar.gz"; \
	fi
	@if [ -f .env ]; then \
		DATE=$$(date +%Y%m%d_%H%M%S); \
		cp .env backups/config_$$DATE.env; \
		echo "✅ Configuration backup: backups/config_$$DATE.env"; \
	fi

# Clean up containers, images, and volumes
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@docker system prune -f
	@echo "✅ Cleanup complete."

# Status check
status:
	@echo "📊 System Status:"
	@echo "=================="
	@docker-compose ps

# Install dependencies (for local development)
install:
	@echo "📦 Installing Python dependencies..."
	@pip install -r requirements.txt
	@echo "✅ Dependencies installed."

# Database operations
db-migrate:
	@echo "🗄️  Running database migrations..."
	@docker-compose exec face-recognition-app python -c "from models import db; db.create_all(); print('Database initialized')"

db-reset:
	@echo "⚠️  Resetting database..."
	@docker-compose down -v
	@rm -f data/attendance.db
	@docker-compose up -d
	@sleep 5
	@make db-migrate

# Monitor system resources
monitor:
	@echo "📈 System Resource Usage:"
	@docker stats --no-stream

# View specific service logs
logs-app:
	@docker-compose logs -f face-recognition-app

logs-db:
	@docker-compose logs -f postgres

# Quick commands
quick-start: start
	@echo ""
	@echo "🎉 Face Recognition Attendance System is ready!"
	@echo "   Visit http://localhost:5000 to get started"

# Update system
update:
	@echo "🔄 Updating system..."
	@git pull
	@docker-compose pull
	@make build
	@make restart
	@echo "✅ System updated!" 