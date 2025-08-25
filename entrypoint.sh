# Use an official Python runtime as a parent image
FROM python:3.12-slim
LABEL authors="jayesh"

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for runtime download
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./app ./app

# Copy the new entrypoint script and make it executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# The entrypoint script will run on container startup
ENTRYPOINT ["/app/entrypoint.sh"]

# The default command to be executed by the entrypoint script
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]