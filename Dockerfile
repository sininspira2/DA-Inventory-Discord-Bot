# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code into the container
COPY . .

# The PORT environment variable is automatically set by Cloud Run.
# Gunicorn will run the FastAPI app defined as 'app' in the 'bot.py' file.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "bot:app"]
