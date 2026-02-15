#!/bin/bash
echo "🔄 Restarting Car Arbitrage Server..."
sudo systemctl restart car-arbitrage
sleep 2
sudo systemctl status car-arbitrage --no-pager -l
echo ""
echo "✅ Server restarted. Check status above."
