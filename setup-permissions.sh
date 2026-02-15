#!/bin/bash
# Setup executable permissions for Car Arbitrage Scraper

echo "Setting up file permissions..."

# Make Python scripts executable
chmod +x car_scraper.py
chmod +x app.py

# Make this script executable (for future runs)
chmod +x setup-permissions.sh

echo "✅ Permissions set:"
echo "   - car_scraper.py (executable)"
echo "   - app.py (executable)"
echo ""
echo "You can now run:"
echo "   ./car_scraper.py --demo"
echo "   ./app.py"
