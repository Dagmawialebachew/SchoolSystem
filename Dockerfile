FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create directory for media files
RUN mkdir -p /app/media

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "SchoolSystem.wsgi:application"]