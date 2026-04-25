# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port
EXPOSE 5000


# Run the app
CMD ["python", "app.py"]