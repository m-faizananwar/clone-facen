#!/bin/bash

# Face Recognition Attendance System - Startup Script
# This script helps you quickly deploy the system using Docker

set -e

echo "🚀 Face Recognition Attendance System Deployment"
echo "================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data uploads face_templates logs exports backups

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚙️  Creating environment configuration..."
    cat > .env << EOF
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Database Configuration
DATABASE_URL=sqlite:///data/attendance.db

# Face Recognition Configuration
FACE_RECOGNITION_MODEL=GhostFaceNet
ANTI_SPOOFING_ENABLED=true

# File Upload Configuration
MAX_UPLOAD_SIZE=16777216

# PostgreSQL Configuration (if using PostgreSQL)
POSTGRES_DB=attendance_db
POSTGRES_USER=face_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
EOF
    echo "✅ Environment file created (.env)"
else
    echo "✅ Environment file already exists (.env)"
fi

# Build and start the services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running successfully!"
    echo ""
    echo "🌐 Access the application:"
    echo "   - Web Interface: http://localhost:5000"
    echo "   - Database Admin: http://localhost:8080"
    echo "   - Health Check: http://localhost:5000/health"
    echo ""
    echo "📋 Quick Start Guide:"
    echo "   1. Open http://localhost:5000 in your browser"
    echo "   2. Click 'Enroll Employee' to add your first employee"
    echo "   3. Use 'Mark Attendance' to test face recognition"
    echo ""
    echo "📖 For detailed documentation, see README.md"
    echo ""
    echo "🔧 Useful commands:"
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop system: docker-compose down"
    echo "   - Restart: docker-compose restart"
    echo ""
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "   docker-compose logs"
    exit 1
fi

# Check camera access (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -e /dev/video0 ]; then
        echo "📷 Camera device detected: /dev/video0"
    else
        echo "⚠️  No camera device found. Make sure your camera is connected."
        echo "   You can check available cameras with: ls /dev/video*"
    fi
fi

echo ""
echo "🎉 Face Recognition Attendance System is ready!"
echo "   Visit http://localhost:5000 to get started" 