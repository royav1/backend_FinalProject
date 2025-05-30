# backend/Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev curl

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Expose port for Django dev server (optional for dev use)
EXPOSE 8000

# Start the development server by default (can override in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
