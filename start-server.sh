#!/bin/bash
#
# Car Arbitrage Server - Easy Start Script
# Just run: ./start-server.sh
#

set -e

echo "=========================================="
echo "  🚀 Car Arbitrage Server Startup"
echo "=========================================="
echo ""

# Get current directory and user
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="$(whoami)"

echo "📁 Working directory: $SCRIPT_DIR"
echo "👤 Running as user: $CURRENT_USER"
echo ""

# Make Python scripts executable
echo "🔧 Setting file permissions..."
chmod +x car_scraper.py app.py 2>/dev/null || true
chmod +x start-server.sh 2>/dev/null || true

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "✅ Virtual environment found"
fi

# Create systemd service file with correct paths
echo "🔧 Configuring systemd service..."
cat <<EOF | sudo tee /etc/systemd/system/car-arbitrage.service > /dev/null
[Unit]
Description=Car Arbitrage Web Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin"
ExecStart=$SCRIPT_DIR/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable service
echo "⚙️  Enabling auto-start on boot..."
sudo systemctl enable car-arbitrage 2>/dev/null || true

# Stop if already running
echo "🛑 Stopping any existing service..."
sudo systemctl stop car-arbitrage 2>/dev/null || true

# Start the service
echo "🚀 Starting Car Arbitrage service..."
sudo systemctl start car-arbitrage

# Wait a moment for startup
sleep 2

# Check status
echo ""
echo "=========================================="
echo "  📊 Service Status"
echo "=========================================="
sudo systemctl status car-arbitrage --no-pager -l

# Check if it's running
if sudo systemctl is-active --quiet car-arbitrage; then
    echo ""
    echo "=========================================="
    echo "  ✅ SUCCESS! Server is running"
    echo "=========================================="
    echo ""

    # Get public IP (try multiple methods)
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || hostname -I | awk '{print $1}')

    if [ -n "$PUBLIC_IP" ]; then
        echo "🌐 Access your application at:"
        echo ""
        echo "   Dashboard:  http://$PUBLIC_IP/"
        echo "   API:        http://$PUBLIC_IP/api/deals"
        echo "   Status:     http://$PUBLIC_IP/api/status"
        echo "   Health:     http://$PUBLIC_IP/health"
        echo ""
    fi

    echo "📋 Useful commands:"
    echo "   sudo systemctl status car-arbitrage   # Check status"
    echo "   sudo systemctl stop car-arbitrage     # Stop server"
    echo "   sudo systemctl restart car-arbitrage  # Restart server"
    echo "   sudo journalctl -u car-arbitrage -f   # View logs"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "  ❌ ERROR: Service failed to start"
    echo "=========================================="
    echo ""
    echo "📋 View logs with:"
    echo "   sudo journalctl -u car-arbitrage -n 50"
    echo ""
    exit 1
fi
