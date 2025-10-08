#!/bin/bash
# Railway build script for Django

echo "Starting Django build process..."

# Set Python path
export PYTHONPATH=/app

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

echo "Build completed successfully!"
