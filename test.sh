#!/bin/bash

# Exit on error
set -e

# Check if the .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# API Keys
OPENAI_API_KEY=
TAVILY_API_KEY=

# Model configuration
OPENAI_MODEL=gpt-4o

# Other configurations
MAX_RETRIES=3
REQUEST_TIMEOUT=30
EOF
    echo ".env file created. Please edit it to add your API keys."
    exit 1
fi

# Ensure we have a resume.yaml file
if [ ! -f resume.yaml ]; then
    echo "Using provided resume.yaml in the workspace"
fi

# Run the main program with the sample job description
echo "Running resume customizer with sample job description..."
./customize_resume.py --resume resume.yaml --job-description data/sample_job_description.txt --output customized_resume.md

echo "Done! Customized resume saved to customized_resume.md"

# Display the first few lines of the output
echo ""
echo "Preview of the customized resume:"
echo "=================================="
head -n 20 customized_resume.md

echo ""
echo "To view the full resume, open 'customized_resume.md'" 