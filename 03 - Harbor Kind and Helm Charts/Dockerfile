# Dockerfile for building the Python Flask application image

# Use the official Python image as base
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container at /app
COPY . .

# Expose port 8080 to the outside world
EXPOSE 8080

# Command to run the Flask application
CMD ["python", "hot-cold.py"]