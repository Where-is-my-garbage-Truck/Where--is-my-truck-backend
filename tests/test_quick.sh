#!/bin/bash
# Quick API Test Script
# Usage: ./test_quick.sh [base_url]

BASE_URL="${1:-http://localhost:8000}"
echo "🚛 Testing Garbage Truck Tracker API"
echo "Base URL: $BASE_URL"
echo "=================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo "  $method $endpoint"
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "  ${GREEN}✅ Status: $http_code${NC}"
    else
        echo -e "  ${RED}❌ Status: $http_code${NC}"
    fi
    echo "  Response: $body" | head -c 200
    echo ""
}

# ============ RUN TESTS ============

echo ""
echo "========== HEALTH CHECK =========="
test_endpoint "GET" "/health" "" "Server Health"

echo ""
echo "========== ZONE MANAGEMENT =========="
test_endpoint "POST" "/zones/" \
    '{"name":"Test Ward","city":"Bangalore","min_lat":12.90,"max_lat":12.98,"min_lng":77.55,"max_lng":77.65}' \
    "Create Zone"

test_endpoint "GET" "/zones/" "" "List Zones"

echo ""
echo "========== TRUCK MANAGEMENT =========="
test_endpoint "POST" "/truck/" \
    '{"vehicle_number":"KA99ZZ9999","driver_name":"Test Driver","driver_phone":"9999999999","zone_id":1}' \
    "Create Truck"

test_endpoint "GET" "/truck/all" "" "List Trucks"

echo ""
echo "========== DRIVER APP =========="
test_endpoint "POST" "/truck/login" \
    '{"phone":"9999999999"}' \
    "Driver Login"

test_endpoint "POST" "/truck/1/start" "" "Start Duty"

test_endpoint "POST" "/truck/1/location" \
    "{\"lat\":12.95,\"lng\":77.58,\"speed\":15,\"heading\":90,\"captured_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
    "Send Location"

echo ""
echo "========== USER MANAGEMENT =========="
test_endpoint "POST" "/user/register" \
    '{"name":"Test User","phone":"8888888888","home_lat":12.94,"home_lng":77.60,"home_address":"Test Address"}' \
    "Register User"

test_endpoint "PUT" "/user/1/home" \
    '{"home_lat":12.94,"home_lng":77.60,"home_address":"Test Address"}' \
    "Update Home"

echo ""
echo "========== TRACKING =========="
test_endpoint "GET" "/track/1" "" "Track Truck"
test_endpoint "GET" "/track/1/route?minutes=60" "" "Route History"
test_endpoint "GET" "/track/nearby?lat=12.94&lng=77.60&radius_km=10" "" "Nearby Trucks"

echo ""
echo "========== CLEANUP =========="
test_endpoint "POST" "/truck/1/stop" "" "Stop Duty"

echo ""
echo "========== DEBUG =========="
test_endpoint "GET" "/debug/db" "" "Database State"

echo ""
echo "=================================="
echo -e "${GREEN}Tests completed!${NC}"
echo "Open $BASE_URL/docs for Swagger UI"