# Use an official Python runtime as a parent image
FROM python:3.12-slim
LABEL authors="jayesh"

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for downloading and unzipping
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# We create a virtual environment for best practices
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./app ./app

# --- Kaggle Dataset Download using cURL ---
# The user must provide their Kaggle API credentials as build arguments
# docker build --build-arg KAGGLE_USERNAME=... --build-arg KAGGLE_KEY=... -t sql-query-ui .

# Download the dataset using cURL with basic authentication
RUN curl -L \
  -o /app/dataset.zip \
  "https://www.kaggle.com/api/v1/datasets/download/asaniczka/amazon-uk-products-dataset-2023"

# Unzip the dataset and clean up the zip file to reduce image size
RUN unzip /app/dataset.zip -d /app && rm /app/dataset.zip
ENV DATA_FILE_PATH="/app/amz_uk_processed_data.csv"

# Expose the port Streamlit runs on
EXPOSE 8501

# Define the command to run the application
# Use the healthcheck to ensure Streamlit has started before marking the container as healthy
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
