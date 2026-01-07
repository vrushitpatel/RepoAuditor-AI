#!/bin/bash

# Setup script for RepoAuditor AI

set -e

echo "=== RepoAuditor AI Setup ==="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

if ! python -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "Error: Python 3.11 or higher is required"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -e .

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ".env file created - please update with your credentials"
else
    echo ".env file already exists"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Update .env file with your credentials"
echo "2. Add your GitHub App private key to the project root"
echo "3. Run 'source venv/bin/activate' (or 'venv\\Scripts\\activate' on Windows)"
echo "4. Run 'bash scripts/dev.sh' to start the development server"
echo ""
