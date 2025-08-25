#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Define file paths for data management
DATA_DIR="/app/data"
DATA_FILE_PATH="${DATA_DIR}/amz_uk_processed_data.csv"
ZIP_FILE_PATH="${DATA_DIR}/dataset.zip"

# Ensure the data directory exists
mkdir -p $DATA_DIR

# Check if the data file already exists in the persistent volume.
if [ ! -f "$DATA_FILE_PATH" ]; then
    echo "[INFO] Dataset not found at ${DATA_FILE_PATH}."


    echo "[INFO] Starting dataset download from Kaggle..."
    curl -L -o "$ZIP_FILE_PATH" \
      "https://www.kaggle.com/api/v1/datasets/download/asaniczka/amazon-uk-products-dataset-2023"

    echo "[INFO] Download complete. Unzipping dataset..."
    unzip "$ZIP_FILE_PATH" -d "$DATA_DIR"

    echo "[INFO] Unzip complete. Cleaning up archive file..."
    rm "$ZIP_FILE_PATH"

    echo "[INFO] Dataset preparation is complete."
else
    echo "[INFO] Existing dataset found at ${DATA_FILE_PATH}. Re-using it."
fi

# Execute the command passed into this script (the CMD from the Dockerfile).
# This will start the Streamlit server.
echo "[INFO] Starting Streamlit application server."
exec "$@"