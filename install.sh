#!/bin/bash
# GPX Routes Manager - Installation Script

set -e

echo "========================================="
echo "GPX Routes Manager - Installation"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Ask about Playwright
echo "Do you want to install Playwright for high-quality map thumbnails?"
echo "Without it, thumbnails will be simple route lines (still functional)."
read -p "Install Playwright? (y/n): " install_playwright

if [ "$install_playwright" = "y" ] || [ "$install_playwright" = "Y" ]; then
    echo "Installing Playwright and Chromium browser..."
    playwright install chromium
    echo "✓ Playwright installed"
else
    echo "⊘ Skipping Playwright (thumbnails will use matplotlib)"
fi
echo ""

# Setup environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your Backblaze B2 credentials!"
    echo ""
else
    echo "⊘ .env file already exists"
    echo ""
fi

# Run migrations
echo "Setting up database..."
python3 manage.py makemigrations
python3 manage.py migrate
echo "✓ Database created"
echo ""

# Create superuser
echo "Creating admin user..."
echo "You'll use these credentials to log in and share with others."
python3 manage.py createsuperuser
echo ""

echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Backblaze B2 credentials"
echo "2. Run: python3 manage.py runserver"
echo "3. Visit: http://localhost:8000"
echo ""
echo "For help, see QUICKSTART.md"
echo ""
