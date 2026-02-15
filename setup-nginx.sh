#!/bin/bash
#
# Setup Nginx for Car Arbitrage
#

set -e

echo "=========================================="
echo "  🔧 Nginx Configuration Setup"
echo "=========================================="
echo ""

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing nginx..."
    sudo apt update
    sudo apt install -y nginx
else
    echo "✅ Nginx is already installed"
fi

# Copy nginx configuration
echo "📝 Copying nginx configuration..."
sudo cp "$SCRIPT_DIR/nginx-site.conf" /etc/nginx/sites-available/car-arbitrage

# Remove default site
echo "🗑️  Removing default nginx site..."
sudo rm -f /etc/nginx/sites-enabled/default

# Enable car-arbitrage site
echo "✅ Enabling car-arbitrage site..."
sudo ln -sf /etc/nginx/sites-available/car-arbitrage /etc/nginx/sites-enabled/

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
sudo nginx -t

# Restart nginx
echo "🔄 Restarting nginx..."
sudo systemctl restart nginx

# Check nginx status
if sudo systemctl is-active --quiet nginx; then
    echo ""
    echo "=========================================="
    echo "  ✅ Nginx configured successfully!"
    echo "=========================================="
    echo ""

    # Get public IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || hostname -I | awk '{print $1}')

    echo "🌐 Access your app at: http://$PUBLIC_IP"
    echo ""
else
    echo ""
    echo "❌ Nginx failed to start"
    echo "Check logs: sudo journalctl -u nginx -n 50"
    echo ""
    exit 1
fi
