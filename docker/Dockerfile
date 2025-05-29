FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy only requirements first for better layer caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ./

# Expose the port the app listens on
EXPOSE 8002

# Run the server
CMD ["python", "server.py"]
