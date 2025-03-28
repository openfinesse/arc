#!/bin/bash

# Exit on error
set -e

# Check if the .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# API Keys
OPENAI_API_KEY=
PERPLEXITY_API_KEY=

# Model configuration
OPENAI_MODEL=gpt-4o
PERPLEXITY_MODEL=sonar-pro-online

# Other configurations
MAX_RETRIES=3
REQUEST_TIMEOUT=30
EOF
    echo ".env file created. Please edit it to add your API keys."
    exit 1
fi

# Check if resume.yaml is in the current directory
if [ ! -f resume.yaml ]; then
    echo "Warning: resume.yaml not found in current directory."
    echo "Using the provided example resume.yaml"
    RESUME_PATH="./resume.yaml"
else
    RESUME_PATH="./resume.yaml"
fi

# Check if a job description file was provided
if [ -z "$1" ]; then
    echo "No job description file provided. Using sample job description."
    JOB_DESC_PATH="./data/sample_job_description.txt"
else
    JOB_DESC_PATH="$1"
    if [ ! -f "$JOB_DESC_PATH" ]; then
        echo "Job description file not found: $JOB_DESC_PATH"
        exit 1
    fi
fi

# Set output path
if [ -z "$2" ]; then
    OUTPUT_PATH="./customized_resume.md"
else
    OUTPUT_PATH="$2"
fi

# Load environment variables
source .env

# Run the program
echo "Running resume customizer..."
echo "Resume: $RESUME_PATH"
echo "Job Description: $JOB_DESC_PATH"
echo "Output: $OUTPUT_PATH"
python src/main.py --resume "$RESUME_PATH" --job-description "$JOB_DESC_PATH" --output "$OUTPUT_PATH"

# Convert Markdown to PDF
pandoc -s "$OUTPUT_PATH" -o "$OUTPUT_PATH.pdf" --pdf-engine=xelatex --template=templates/default.tex

echo "PDF version saved to $OUTPUT_PATH.pdf" 