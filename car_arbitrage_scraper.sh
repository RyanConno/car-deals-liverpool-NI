#!/bin/bash

#############################################################################
# CAR ARBITRAGE SCRAPER - Liverpool to Northern Ireland
# Finds drift/race scene cars for profitable resale
# Target: Cars within 100 miles of Liverpool, sell in NI market
#############################################################################

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
LIVERPOOL_LAT="53.4084"
LIVERPOOL_LON="-2.9916"
MAX_DISTANCE_MILES=100
OUTPUT_DIR="./car_deals"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="${OUTPUT_DIR}/deals_${TIMESTAMP}.csv"
HTML_REPORT="${OUTPUT_DIR}/report_${TIMESTAMP}.html"

# Target models for drift/race scene (high profit potential)
declare -A TARGET_MODELS=(
    ["bmw_e46"]="BMW 3-Series E46 330i|BMW 330i|BMW 330ci|E46 330"
    ["bmw_e36"]="BMW E36 M3|BMW E36 328i|BMW 328i E36|E36 M3"
    ["lexus_is200"]="Lexus IS200|Lexus IS300|IS200|IS300"
    ["nissan_200sx"]="Nissan 200SX|Nissan Silvia|200SX S13|200SX S14|S13|S14|S15"
    ["nissan_skyline"]="Nissan Skyline|R33 GTS-T|Skyline GTR"
    ["honda_civic"]="Honda Civic Type R|Civic Type-R|EP3|FN2"
    ["mazda_rx"]="Mazda RX-7|Mazda RX-8|RX7|RX8"
    ["subaru_impreza"]="Subaru Impreza WRX|Subaru STI|Impreza STI"
    ["mitsubishi_evo"]="Mitsubishi Evo|Lancer Evolution|Evo 8|Evo 9"
    ["toyota_supra"]="Toyota Supra|Supra MK4"
)

# Price ranges (max purchase price for profitability)
declare -A MAX_PRICES=(
    ["bmw_e46"]=10000
    ["bmw_e36"]=8000
    ["lexus_is200"]=5000
    ["nissan_200sx"]=20000
    ["nissan_skyline"]=25000
    ["honda_civic"]=12000
    ["mazda_rx"]=15000
    ["subaru_impreza"]=12000
    ["mitsubishi_evo"]=15000
    ["toyota_supra"]=35000
)

# Expected NI markup (conservative estimates)
declare -A NI_MARKUP=(
    ["bmw_e46"]=2000
    ["bmw_e36"]=1800
    ["lexus_is200"]=1200
    ["nissan_200sx"]=4000
    ["nissan_skyline"]=5000
    ["honda_civic"]=2500
    ["mazda_rx"]=3000
    ["subaru_impreza"]=2500
    ["mitsubishi_evo"]=3500
    ["toyota_supra"]=6000
)

#############################################################################
# Functions
#############################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "   CAR ARBITRAGE FINDER - Liverpool → Northern Ireland"
    echo "   Drift & Race Scene Vehicles"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

setup_directories() {
    mkdir -p "${OUTPUT_DIR}"
    echo -e "${GREEN}✓${NC} Output directory created: ${OUTPUT_DIR}"
}

# Calculate distance between two coordinates (Haversine formula)
calculate_distance() {
    local lat1=$1
    local lon1=$2
    local lat2=$3
    local lon2=$4
    
    # Using bc for floating point math
    local distance=$(awk -v lat1="$lat1" -v lon1="$lon1" -v lat2="$lat2" -v lon2="$lon2" 'BEGIN {
        PI = 3.14159265358979323846
        lat1_rad = lat1 * PI / 180
        lat2_rad = lat2 * PI / 180
        delta_lat = (lat2 - lat1) * PI / 180
        delta_lon = (lon2 - lon1) * PI / 180
        
        a = sin(delta_lat/2) * sin(delta_lat/2) + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2) * sin(delta_lon/2)
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = 3959 * c  # Earth radius in miles
        
        printf "%.1f", distance
    }')
    
    echo "$distance"
}

# Scrape AutoTrader (simulation - would need real API/scraping)
scrape_autotrader() {
    local model_key=$1
    local search_term="${TARGET_MODELS[$model_key]}"
    
    echo -e "${YELLOW}→${NC} Searching AutoTrader for: ${search_term}"
    
    # NOTE: This is a simulation. Real implementation would use:
    # - curl with proper headers
    # - BeautifulSoup/cheerio for HTML parsing
    # - Or official APIs if available
    
    # Simulated results (in real version, this would scrape actual data)
    cat << EOF
{
    "results": [
        {"title": "BMW E46 330i Manual", "price": 8500, "location": "Manchester", "lat": 53.4808, "lon": -2.2426, "url": "https://autotrader.co.uk/example1", "mileage": 89000, "year": 2004},
        {"title": "Lexus IS200 Sport", "price": 4200, "location": "Chester", "lat": 53.1908, "lon": -2.8908, "url": "https://autotrader.co.uk/example2", "mileage": 112000, "year": 2003}
    ]
}
EOF
}

# Scrape PistonHeads (simulation)
scrape_pistonheads() {
    local model_key=$1
    echo -e "${YELLOW}→${NC} Searching PistonHeads for: ${TARGET_MODELS[$model_key]}"
    
    # Simulated results
    cat << EOF
{
    "results": [
        {"title": "Nissan 200SX S14", "price": 16500, "location": "Preston", "lat": 53.7632, "lon": -2.7031, "url": "https://pistonheads.com/example", "mileage": 95000, "year": 1999}
    ]
}
EOF
}

# Scrape Gumtree (simulation)
scrape_gumtree() {
    local model_key=$1
    echo -e "${YELLOW}→${NC} Searching Gumtree for: ${TARGET_MODELS[$model_key]}"
    
    cat << EOF
{
    "results": [
        {"title": "BMW E36 328i Sport", "price": 5800, "location": "Warrington", "lat": 53.3900, "lon": -2.5970, "url": "https://gumtree.com/example", "mileage": 145000, "year": 1998}
    ]
}
EOF
}

# Initialize CSV file
init_csv() {
    echo "Model,Title,Price,Expected_NI_Price,Profit_Est,Location,Distance_Miles,Year,Mileage,URL,Profit_Margin" > "$RESULTS_FILE"
}

# Calculate profit and filter deals
process_listing() {
    local model_key=$1
    local title=$2
    local price=$3
    local lat=$4
    local lon=$5
    local location=$6
    local url=$7
    local mileage=$8
    local year=$9
    
    # Calculate distance from Liverpool
    local distance=$(calculate_distance "$LIVERPOOL_LAT" "$LIVERPOOL_LON" "$lat" "$lon")
    
    # Check if within range
    if (( $(echo "$distance <= $MAX_DISTANCE_MILES" | bc -l) )); then
        # Check if price is profitable
        local max_price=${MAX_PRICES[$model_key]}
        local markup=${NI_MARKUP[$model_key]}
        
        if [ "$price" -le "$max_price" ]; then
            local ni_price=$((price + markup))
            local costs=450  # Ferry, fuel, insurance
            local net_profit=$((markup - costs))
            local profit_margin=$(awk -v profit="$net_profit" -v price="$price" 'BEGIN {printf "%.1f", (profit/price)*100}')
            
            # Only show deals with >£500 net profit
            if [ "$net_profit" -gt 500 ]; then
                echo -e "${GREEN}✓ GOOD DEAL:${NC} $title - £${price} → £${ni_price} (${MAGENTA}+£${net_profit}${NC} profit)"
                
                # Add to CSV
                echo "\"$model_key\",\"$title\",\"£$price\",\"£$ni_price\",\"£$net_profit\",\"$location\",\"$distance\",\"$year\",\"$mileage\",\"$url\",\"$profit_margin%\"" >> "$RESULTS_FILE"
                
                return 0
            fi
        fi
    fi
    
    return 1
}

# Main scraping function
scrape_all_sources() {
    local deals_found=0
    
    echo -e "\n${BLUE}Starting scrape...${NC}\n"
    
    for model_key in "${!TARGET_MODELS[@]}"; do
        echo -e "\n${CYAN}━━━ Searching for: ${model_key} ━━━${NC}"
        
        # Scrape AutoTrader
        local at_results=$(scrape_autotrader "$model_key")
        
        # Parse JSON (in real implementation, use jq)
        # This is simplified demonstration
        
        # Process simulated results
        process_listing "$model_key" "BMW E46 330i Manual" 8500 53.4808 -2.2426 "Manchester" "https://autotrader.co.uk/1" 89000 2004 && ((deals_found++))
        
        process_listing "$model_key" "Lexus IS200 Sport" 4200 53.1908 -2.8908 "Chester" "https://autotrader.co.uk/2" 112000 2003 && ((deals_found++))
        
        # Scrape PistonHeads
        process_listing "$model_key" "Nissan 200SX S14" 16500 53.7632 -2.7031 "Preston" "https://pistonheads.com/1" 95000 1999 && ((deals_found++))
        
        # Scrape Gumtree
        process_listing "$model_key" "BMW E36 328i Sport" 5800 53.3900 -2.5970 "Warrington" "https://gumtree.com/1" 145000 1998 && ((deals_found++))
        
        sleep 1  # Be respectful to servers
    done
    
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Total profitable deals found: ${deals_found}${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Generate HTML report
generate_html_report() {
    # First, prepare the data from CSV
    local csv_data=""
    if [ -f "$RESULTS_FILE" ]; then
        # Convert CSV to JavaScript array (skip header)
        csv_data=$(tail -n +2 "$RESULTS_FILE" | awk -F',' '{
            gsub(/"/, "", $0);
            printf "{model:\"%s\",title:\"%s\",price:\"%s\",ni_price:\"%s\",profit:\"%s\",location:\"%s\",distance:\"%s\",year:\"%s\",mileage:\"%s\",url:\"%s\",margin:\"%s\"},\n", 
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
        }')
    fi
    
    cat > "$HTML_REPORT" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Car Arbitrage Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        h1 { 
            color: #00ff88;
            margin: 30px 0;
            font-size: 2.5em;
            text-align: center;
            text-shadow: 0 0 20px rgba(0,255,136,0.5);
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #00ff8833;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        .stat-value {
            font-size: 2.5em;
            color: #00ff88;
            font-weight: bold;
        }
        .stat-label {
            color: #888;
            margin-top: 10px;
            font-size: 0.9em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            background: #1a1f3a;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }
        th {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #0a0e27;
            padding: 18px 12px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 0.5px;
        }
        td {
            padding: 16px 12px;
            border-bottom: 1px solid #2a2f4a;
            font-size: 0.9em;
        }
        tr:hover {
            background: #252a45;
        }
        .profit { 
            color: #00ff88;
            font-weight: bold;
            font-size: 1.1em;
        }
        .price { color: #ffaa00; font-weight: 600; }
        .location { color: #6666ff; }
        .model-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: 600;
            background: #2a2f4a;
            color: #00ff88;
            border: 1px solid #00ff8844;
        }
        .high-profit { 
            background: #00ff8822; 
            color: #00ff88; 
            border: 1px solid #00ff88;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: bold;
        }
        .medium-profit { 
            background: #ffaa0022; 
            color: #ffaa00; 
            border: 1px solid #ffaa00;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: bold;
        }
        a { 
            color: #6666ff; 
            text-decoration: none;
            font-weight: 600;
        }
        a:hover { 
            color: #8888ff; 
            text-decoration: underline; 
        }
        .timestamp {
            text-align: center;
            color: #666;
            margin-top: 40px;
            font-size: 0.9em;
        }
        .no-data {
            text-align: center;
            padding: 60px 20px;
            color: #888;
            font-size: 1.2em;
        }
        .car-title {
            font-weight: 600;
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏎️ Car Arbitrage Opportunities</h1>
        <p style="text-align: center; color: #888; margin-bottom: 40px;">
            Liverpool → Northern Ireland | Drift & Race Scene
        </p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-deals">0</div>
                <div class="stat-label">Profitable Deals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-profit">£0</div>
                <div class="stat-label">Total Potential Profit</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-profit">£0</div>
                <div class="stat-label">Average Profit/Car</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="best-margin">0%</div>
                <div class="stat-label">Best Profit Margin</div>
            </div>
        </div>
        
        <table id="deals-table">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Title</th>
                    <th>Buy Price</th>
                    <th>Sell Price (NI)</th>
                    <th>Net Profit</th>
                    <th>Margin</th>
                    <th>Location</th>
                    <th>Distance</th>
                    <th>Details</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody id="deals-body">
            </tbody>
        </table>
        
        <div class="timestamp">
            Generated: <span id="timestamp"></span>
        </div>
    </div>
    
    <script>
        // Car data from CSV
        const carData = [
            ${csv_data}
        ];
        
        // Populate timestamp
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
        
        // Calculate statistics
        if (carData.length > 0) {
            const totalDeals = carData.length;
            const totalProfit = carData.reduce((sum, car) => {
                const profit = parseInt(car.profit.replace(/[£,]/g, ''));
                return sum + profit;
            }, 0);
            const avgProfit = Math.round(totalProfit / totalDeals);
            const bestMargin = Math.max(...carData.map(car => 
                parseFloat(car.margin.replace('%', ''))
            ));
            
            // Update stats
            document.getElementById('total-deals').textContent = totalDeals;
            document.getElementById('total-profit').textContent = '£' + totalProfit.toLocaleString();
            document.getElementById('avg-profit').textContent = '£' + avgProfit.toLocaleString();
            document.getElementById('best-margin').textContent = bestMargin.toFixed(1) + '%';
            
            // Populate table
            const tbody = document.getElementById('deals-body');
            carData.forEach(car => {
                const profit = parseInt(car.profit.replace(/[£,]/g, ''));
                const profitClass = profit > 2000 ? 'high-profit' : 'medium-profit';
                
                const row = document.createElement('tr');
                row.innerHTML = \`
                    <td><span class="model-badge">\${car.model}</span></td>
                    <td class="car-title">\${car.title}</td>
                    <td class="price">\${car.price}</td>
                    <td class="price">\${car.ni_price}</td>
                    <td><span class="\${profitClass}">\${car.profit}</span></td>
                    <td>\${car.margin}</td>
                    <td class="location">\${car.location}</td>
                    <td>\${car.distance} mi</td>
                    <td>\${car.year} | \${car.mileage} mi</td>
                    <td><a href="\${car.url}" target="_blank">View Listing →</a></td>
                \`;
                tbody.appendChild(row);
            });
        } else {
            // Show no data message
            const tbody = document.getElementById('deals-body');
            tbody.innerHTML = '<tr><td colspan="10" class="no-data">No profitable deals found yet. Run the scraper to find opportunities!</td></tr>';
        }
    </script>
</body>
</html>
HTMLEOF
    
    echo -e "${GREEN}✓${NC} HTML report generated: ${HTML_REPORT}"
}

# Display summary
show_summary() {
    if [ -f "$RESULTS_FILE" ]; then
        local deal_count=$(tail -n +2 "$RESULTS_FILE" | wc -l)
        
        echo -e "\n${CYAN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}                    SUMMARY${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
        echo -e "Deals found:     ${GREEN}${deal_count}${NC}"
        echo -e "Results saved:   ${BLUE}${RESULTS_FILE}${NC}"
        echo -e "HTML report:     ${BLUE}${HTML_REPORT}${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}\n"
        
        if [ "$deal_count" -gt 0 ]; then
            echo -e "${YELLOW}Top 5 Deals:${NC}\n"
            tail -n +2 "$RESULTS_FILE" | sort -t',' -k5 -rn | head -5 | while IFS=',' read -r model title price ni_price profit location distance year mileage url margin; do
                echo -e "${GREEN}▸${NC} ${title}"
                echo -e "  Buy: ${price} → Sell: ${ni_price} | Profit: ${MAGENTA}${profit}${NC} | ${location} (${distance} miles)"
                echo ""
            done
        fi
    fi
}

# Install dependencies check
check_dependencies() {
    local missing=0
    
    echo -e "${BLUE}Checking dependencies...${NC}"
    
    for cmd in curl jq bc awk; do
        if ! command -v $cmd &> /dev/null; then
            echo -e "${RED}✗${NC} Missing: $cmd"
            missing=1
        else
            echo -e "${GREEN}✓${NC} Found: $cmd"
        fi
    done
    
    if [ $missing -eq 1 ]; then
        echo -e "\n${YELLOW}Install missing dependencies:${NC}"
        echo "  Ubuntu/Debian: sudo apt-get install curl jq bc"
        echo "  macOS: brew install curl jq bc"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

#############################################################################
# Main Script
#############################################################################

main() {
    print_banner
    check_dependencies
    setup_directories
    init_csv
    scrape_all_sources
    generate_html_report
    show_summary
    
    echo -e "${GREEN}✓ Script completed successfully!${NC}\n"
    echo -e "Next steps:"
    echo -e "  1. Review deals in: ${BLUE}${RESULTS_FILE}${NC}"
    echo -e "  2. Open HTML report: ${BLUE}${HTML_REPORT}${NC}"
    echo -e "  3. Contact sellers for best opportunities"
    echo -e "  4. Factor in ferry costs (£150), fuel (£50), time\n"
}

# Run main function
main "$@"
