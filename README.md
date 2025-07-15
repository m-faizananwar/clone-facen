# Face Recognition Attendance System

A comprehensive offline face recognition attendance system using GhostFaceNet and anti-spoofing technology, designed to run in Docker containers for easy deployment and scalability.

## Features

- **Advanced Face Recognition**: GhostFaceNet model with 99.76% accuracy
- **Anti-Spoofing Protection**: MiniFASNet liveness detection prevents photo/video attacks
- **Offline Operation**: Works without internet connectivity
- **Real-time Processing**: < 50ms recognition speed
- **Modern Web Interface**: Responsive Bootstrap-based UI
- **Docker Deployment**: Easy setup and scaling
- **Database Support**: SQLite (default) and PostgreSQL
- **Comprehensive Reporting**: Attendance analytics and exports
- **Security Features**: Encrypted data storage and audit trails

## System Requirements

### Minimum Requirements
- CPU: 2 cores, 2.0 GHz
- RAM: 4 GB
- Storage: 10 GB available space
- Camera: USB webcam or built-in camera
- OS: Linux, Windows, or macOS with Docker support

### Recommended Requirements
- CPU: 4 cores, 2.5 GHz or higher
- RAM: 8 GB or more
- Storage: 50 GB SSD
- Camera: HD webcam (720p or higher)
- GPU: Optional CUDA-compatible GPU for enhanced performance

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd assistantce_project
```

### 2. Environment Setup

Create a `.env` file with your configuration:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the configuration
nano .env
```

### 3. Build and Run with Docker

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Access the Application

- **Web Interface**: http://localhost:5000
- **Database Admin**: http://localhost:8080 (Adminer)
- **Health Check**: http://localhost:5000/health

## Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-very-secure-secret-key-change-this

# Database
DATABASE_URL=sqlite:///data/attendance.db

# Face Recognition
FACE_RECOGNITION_MODEL=GhostFaceNet
ANTI_SPOOFING_ENABLED=true

# File Upload
MAX_UPLOAD_SIZE=16777216  # 16MB

# Camera
CAMERA_DEVICE_ID=0
```

### Docker Configuration

The system uses Docker Compose with the following services:

- **face-recognition-app**: Main Flask application
- **postgres**: PostgreSQL database (optional)
- **adminer**: Database administration tool

## Usage Guide

### 1. Employee Enrollment

1. Navigate to the Dashboard
2. Click "Enroll Employee" 
3. Fill in employee details
4. Capture a clear face photo
5. Submit the enrollment

### 2. Mark Attendance

1. Go to "Mark Attendance" page
2. Click "Start Camera"
3. Position face in the guide box
4. Click "Mark Attendance"
5. View confirmation result

### 3. View Reports

1. Access the "Reports" section
2. Select date ranges
3. Export data in CSV, JSON, or Excel formats
4. View attendance analytics

### 4. Manage Employees

1. Navigate to "Employees" page
2. View all enrolled employees
3. Edit employee information
4. Deactivate/reactivate employees

## API Documentation

### Authentication Endpoints

#### Mark Attendance
```http
POST /api/mark_attendance
Content-Type: application/json

{
  "image_data": "data:image/jpeg;base64,..."
}
```

#### Enroll Employee
```http
POST /api/enroll_employee
Content-Type: application/json

{
  "employee_id": "EMP001",
  "name": "John Doe",
  "department": "IT",
  "email": "john@company.com",
  "image_data": "data:image/jpeg;base64,..."
}
```

#### System Statistics
```http
GET /api/system_stats
```

### Response Format

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data
  }
}
```

## Security Features

### Anti-Spoofing Protection
- **Liveness Detection**: Detects real human faces vs photos/videos
- **Texture Analysis**: Analyzes skin texture patterns
- **Frequency Domain Analysis**: Detects screen replay attacks
- **Color Distribution**: Identifies printed photos

### Data Security
- **Encrypted Storage**: Face templates stored as encrypted arrays
- **Secure Sessions**: Flask session management
- **Audit Logging**: Complete activity trail
- **Access Control**: Role-based permissions

## Performance Optimization

### Hardware Optimization
- Use SSD storage for faster database operations
- Allocate sufficient RAM for model loading
- Consider GPU acceleration for large deployments

### Software Optimization
- Adjust recognition threshold based on accuracy requirements
- Configure camera resolution for optimal speed/quality balance
- Use PostgreSQL for high-volume deployments

## Troubleshooting

### Common Issues

#### Camera Not Working
```bash
# Check camera permissions
ls /dev/video*

# Test camera access
docker run --rm --device=/dev/video0 face_recognition_attendance python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Error')"
```

#### Database Connection Error
```bash
# Check database status
docker-compose ps

# Reset database
docker-compose down -v
docker-compose up -d
```

#### High Memory Usage
```bash
# Monitor resource usage
docker stats

# Restart services
docker-compose restart face-recognition-app
```

### Log Analysis

```bash
# View application logs
docker-compose logs face-recognition-app

# View error logs
docker exec -it face_recognition_attendance tail -f logs/errors.log

# Check system health
curl http://localhost:5000/health
```

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up development environment
export FLASK_ENV=development
export DATABASE_URL=sqlite:///data/attendance.db

# Create directories
mkdir -p data uploads face_templates logs

# Run application
python app.py
```

### Running Tests

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=. tests/

# Run specific test
pytest tests/test_face_recognition.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Deployment

### Production Deployment

1. **Prepare Environment**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

2. **Configure Security**
   ```bash
   # Set strong passwords
   # Configure firewall
   # Set up SSL/TLS certificates
   ```

3. **Deploy Application**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd face-recognition-attendance
   
   # Configure environment
   cp .env.example .env
   nano .env
   
   # Deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Scaling

For high-volume deployments:

1. **Load Balancing**: Use nginx or HAProxy
2. **Database Clustering**: PostgreSQL with replication
3. **Horizontal Scaling**: Multiple app instances
4. **Monitoring**: Prometheus + Grafana

## Backup and Recovery

### Automated Backups

```bash
# Database backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec postgres pg_dump -U face_user attendance_db > backup_$DATE.sql
```

### Manual Backup

```bash
# Backup database
docker-compose exec postgres pg_dump -U face_user attendance_db > backup.sql

# Backup face templates
tar -czf face_templates_backup.tar.gz face_templates/

# Backup configuration
cp .env config_backup.env
```

### Recovery

```bash
# Restore database
docker-compose exec -T postgres psql -U face_user attendance_db < backup.sql

# Restore face templates
tar -xzf face_templates_backup.tar.gz
```

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:5000/health

# Database health
docker-compose exec postgres pg_isready

# System resources
docker stats
```

### Metrics Collection

The system provides built-in metrics:
- Recognition accuracy rates
- Processing times
- System resource usage
- Error rates and types

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

## Changelog

### Version 1.0.0
- Initial release
- GhostFaceNet integration
- Anti-spoofing protection
- Docker deployment
- Web interface
- Database management
- Reporting features 