#!/bin/bash

set -e # fail if error occurs
python -m ensurepip
# Check for the 'uv' package installer.
if ! command -v uv &> /dev/null
then
    python -m pip install uv
fi
echo ""


# Create  virtual environment.
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    echo "Using existing virtual environment: '.venv' "
else
    echo "Creating virtual environment..."
    uv venv
    echo "The virtual environment has been created successfully."
fi
echo ""


# Install packages.
# Activate the environment so we can install packages into it.
source "$VENV_DIR/bin/activate"

# this is our requirements file where we store packages, we keep it loosely bound to debug issues with new versions when they come
# uv.lock will help us with backward compatability
REQUIREMENTS_FILE="requirements.txt"

if [ -f "$REQUIREMENTS_FILE" ]; then
    uv pip compile requirements.txt -o requirements.txt
else
    echo "Failed to install files as the requirements.txt is missing"
    deactivate
    exit 1
fi
echo ""

