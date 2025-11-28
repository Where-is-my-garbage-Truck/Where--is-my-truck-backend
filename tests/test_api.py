#!/usr/bin/env python3
"""
Garbage Truck Tracker - Complete API Test Suite
================================================
Run this script to test all API endpoints.

Usage:
    python test_api.py [--base-url http://localhost:8000] [--reset]

Options:
    --base-url  : API base URL (default: http://localhost:8000)
    --reset     : Delete database and start fresh before testing
"""

import requests
import json
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# ============ CONFIGURATION ============

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Test data
TEST_ZONE = {
    "name": "Ward 5 - HSR Layout",
    "city": "Bangalore",
    "min_lat": 12.90,
    "max_lat": 12.98,
    "min_lng": 77.55,
    "max_lng": 77.65
}

TEST_TRUCK = {
    "vehicle_number": "KA01AB1234",
    "name": "Truck Alpha",
    "driver_name": "Ramesh Kumar",
    "driver_phone": "9876543210"
}

TEST_USER = {
    "name": "Rahul Sharma",
    "phone": "9123456789",
    "home_lat": 12.94,
    "home_lng": 77.60,
    "home_address": "123, 5th Cross, HSR Layout, Bangalore"
}

# Simulated truck route (approaching user's home)
TRUCK_ROUTE = [
    {"lat": 12.96, "lng": 77.56, "speed": 20, "heading": 135},   # Far - 3km+
    {"lat": 12.955, "lng": 77.57, "speed": 18, "heading": 140},  # Getting closer
    {"lat": 12.950, "lng": 77.58, "speed": 15, "heading": 150},  # 2km
    {"lat": 12.948, "lng": 77.585, "speed": 12, "heading": 160}, # 1.5km
    {"lat": 12.945, "lng": 77.59, "speed": 10, "heading": 170},  # 1km - Approaching alert
    {"lat": 12.943, "lng": 77.595, "speed": 8, "heading": 175},  # 500m - Arriving alert
    {"lat": 12.941, "lng": 77.598, "speed": 5, "heading": 180},  # 200m
    {"lat": 12.9402, "lng": 77.5998, "speed": 3, "heading": 180}, # 50m - Here alert!
]


# ============ HELPER FUNCTIONS ============

class Colors:
    """Terminal colors for pretty output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}\n")


def print_subheader(text: str):
    """Print subsection header"""
    print(f"\n{Colors.CYAN}--- {text} ---{Colors.END}")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")


def print_json(data: dict, indent: int = 2):
    """Pretty print JSON"""
    print(json.dumps(data, indent=indent, default=str))


def api_call(method: str, endpoint: str, data: dict = None, 
             expected_status: int = None) -> tuple:
    """
    Make API call and return (success, response_data)
    """
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=HEADERS)
        elif method == "POST":
            response = requests.post(url, headers=HEADERS, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=HEADERS, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=HEADERS)
        else:
            return False, {"error": f"Unknown method: {method}"}
        
        try:
            response_data = response.json()
        except:
            response_data = {"raw": response.text}
        
        if expected_status:
            success = response.status_code == expected_status
        else:
            success = response.status_code in [200, 201]
        
        return success, response_data
        
    except requests.exceptions.ConnectionError:
        return False, {"error": "Cannot connect to server. Is it running?"}
    except Exception as e:
        return False, {"error": str(e)}


# ============ TEST FUNCTIONS ============

def test_health_check():
    """Test server health"""
    print_subheader("Health Check")
    
    success, data = api_call("GET", "/health")
    if success:
        print_success(f"Server is healthy: {data}")
        return True
    else:
        print_error(f"Server health check failed: {data}")
        return False


def test_create_zone() -> Optional[int]:
    """Test zone creation"""
    print_subheader("Create Zone")
    
    success, data = api_call("POST", "/zones/", TEST_ZONE, expected_status=201)
    if success:
        zone_id = data.get("id")
        print_success(f"Zone created with ID: {zone_id}")
        print_json(data)
        return zone_id
    else:
        # Zone might already exist
        if "already exists" in str(data):
            print_warning("Zone already exists, fetching...")
            success, zones = api_call("GET", "/zones/")
            if success and zones:
                zone_id = zones[0]["id"]
                print_info(f"Using existing zone ID: {zone_id}")
                return zone_id
        print_error(f"Failed to create zone: {data}")
        return None


def test_list_zones():
    """Test listing zones"""
    print_subheader("List Zones")
    
    success, data = api_call("GET", "/zones/")
    if success:
        print_success(f"Found {len(data)} zone(s)")
        for zone in data:
            print(f"  - {zone['name']} (ID: {zone['id']}, Active: {zone['is_active']})")
        return True
    else:
        print_error(f"Failed to list zones: {data}")
        return False


def test_create_truck(zone_id: int) -> Optional[int]:
    """Test truck creation"""
    print_subheader("Create Truck")
    
    truck_data = {**TEST_TRUCK, "zone_id": zone_id}
    success, data = api_call("POST", "/truck/", truck_data, expected_status=201)
    
    if success:
        truck_id = data.get("id")
        print_success(f"Truck created with ID: {truck_id}")
        print_json(data)
        return truck_id
    else:
        if "already exists" in str(data) or "already registered" in str(data):
            print_warning("Truck already exists, fetching...")
            success, trucks = api_call("GET", "/truck/all")
            if success and trucks:
                truck_id = trucks[0]["id"]
                print_info(f"Using existing truck ID: {truck_id}")
                return truck_id
        print_error(f"Failed to create truck: {data}")
        return None


def test_list_trucks():
    """Test listing trucks"""
    print_subheader("List Trucks")
    
    success, data = api_call("GET", "/truck/all")
    if success:
        print_success(f"Found {len(data)} truck(s)")
        for truck in data:
            status = "🟢 Active" if truck['is_active'] else "⚪ Inactive"
            print(f"  - {truck['vehicle_number']} ({status}, Zone: {truck['zone_id']})")
        return True
    else:
        print_error(f"Failed to list trucks: {data}")
        return False


def test_driver_login(phone: str) -> Optional[dict]:
    """Test driver login"""
    print_subheader("Driver Login")
    
    success, data = api_call("POST", "/truck/login", {"phone": phone})
    if success:
        print_success(f"Driver logged in: {data.get('driver_name')}")
        print_json(data)
        return data
    else:
        print_error(f"Driver login failed: {data}")
        return None


def test_start_duty(truck_id: int) -> bool:
    """Test starting duty"""
    print_subheader("Start Duty")
    
    success, data = api_call("POST", f"/truck/{truck_id}/start")
    if success:
        print_success(f"Duty started: {data.get('message')}")
        return True
    else:
        print_error(f"Failed to start duty: {data}")
        return False


def test_stop_duty(truck_id: int) -> bool:
    """Test stopping duty"""
    print_subheader("Stop Duty")
    
    success, data = api_call("POST", f"/truck/{truck_id}/stop")
    if success:
        print_success(f"Duty stopped: {data.get('message')}")
        if data.get('duration'):
            print_info(f"Duration: {data['duration']}")
        return True
    else:
        print_error(f"Failed to stop duty: {data}")
        return False


def test_register_user() -> Optional[int]:
    """Test user registration"""
    print_subheader("Register User")
    
    success, data = api_call("POST", "/user/register", TEST_USER, expected_status=201)
    if success:
        user_id = data.get("id")
        print_success(f"User registered with ID: {user_id}")
        print_json(data)
        
        if data.get("zone_id"):
            print_success(f"Auto-assigned to zone: {data.get('zone_name')}")
        else:
            print_warning("User not assigned to any zone!")
        return user_id
    else:
        if "already registered" in str(data):
            print_warning("User already exists, logging in...")
            success, login_data = api_call("POST", "/user/login", {"phone": TEST_USER["phone"]})
            if success:
                print_info(f"Using existing user ID: {login_data['user_id']}")
                return login_data["user_id"]
        print_error(f"Failed to register user: {data}")
        return None


def test_user_login(phone: str) -> Optional[dict]:
    """Test user login"""
    print_subheader("User Login")
    
    success, data = api_call("POST", "/user/login", {"phone": phone})
    if success:
        print_success(f"User logged in: {data.get('name')}")
        print_json(data)
        return data
    else:
        print_error(f"User login failed: {data}")
        return None


def test_update_user_home(user_id: int) -> bool:
    """Test updating user home location"""
    print_subheader("Update User Home")
    
    home_data = {
        "home_lat": TEST_USER["home_lat"],
        "home_lng": TEST_USER["home_lng"],
        "home_address": TEST_USER["home_address"]
    }
    
    success, data = api_call("PUT", f"/user/{user_id}/home", home_data)
    if success:
        print_success(f"Home updated: {data.get('message')}")
        if data.get('zone_name'):
            print_info(f"Zone: {data['zone_name']}")
        return True
    else:
        print_error(f"Failed to update home: {data}")
        return False


def test_update_user_settings(user_id: int) -> bool:
    """Test updating user settings"""
    print_subheader("Update User Settings")
    
    settings = {
        "alert_enabled": True,
        "alert_distance": 500,
        "alert_type": "sound"
    }
    
    success, data = api_call("PUT", f"/user/{user_id}/settings", settings)
    if success:
        print_success(f"Settings updated")
        print_json(data)
        return True
    else:
        print_error(f"Failed to update settings: {data}")
        return False


def test_send_location(truck_id: int, lat: float, lng: float, 
                       speed: float = 10, heading: float = 0) -> bool:
    """Test sending truck location"""
    location_data = {
        "lat": lat,
        "lng": lng,
        "speed": speed,
        "heading": heading,
        "captured_at": datetime.utcnow().isoformat()
    }
    
    success, data = api_call("POST", f"/truck/{truck_id}/location", location_data)
    if success:
        return True
    else:
        print_error(f"Failed to send location: {data}")
        return False


def test_tracking(user_id: int) -> Optional[dict]:
    """Test main tracking endpoint"""
    success, data = api_call("GET", f"/track/{user_id}")
    if success:
        return data
    else:
        print_error(f"Tracking failed: {data}")
        return None


def test_route_history(user_id: int) -> bool:
    """Test route history endpoint"""
    print_subheader("Route History")
    
    success, data = api_call("GET", f"/track/{user_id}/route?minutes=60")
    if success:
        print_success(f"Route retrieved: {data.get('total_points')} points")
        if data.get('route'):
            print_info(f"From: {data.get('from_time')} To: {data.get('to_time')}")
        return True
    else:
        print_error(f"Failed to get route: {data}")
        return False


def test_nearby_trucks(lat: float, lng: float) -> bool:
    """Test nearby trucks endpoint"""
    print_subheader("Find Nearby Trucks")
    
    success, data = api_call("GET", f"/track/nearby?lat={lat}&lng={lng}&radius_km=10")
    if success:
        print_success(f"Found {data.get('found', 0)} truck(s) nearby")
        for truck in data.get('trucks', []):
            print(f"  - {truck['vehicle_number']}: {truck['distance_text']} away")
        return True
    else:
        print_error(f"Failed to find nearby trucks: {data}")
        return False


def test_zone_status(zone_id: int) -> bool:
    """Test zone truck status endpoint"""
    print_subheader("Zone Truck Status")
    
    success, data = api_call("GET", f"/track/zone/{zone_id}")
    if success:
        print_success(f"Zone: {data.get('zone_name')}")
        if data.get('truck'):
            truck = data['truck']
            status = "🟢 Active" if truck['is_active'] else "⚪ Inactive"
            print(f"  Truck: {truck['vehicle_number']} ({status})")
        else:
            print_warning("No truck assigned to this zone")
        return True
    else:
        print_error(f"Failed to get zone status: {data}")
        return False


def test_offline_sync(truck_id: int) -> bool:
    """Test offline location sync"""
    print_subheader("Offline Sync")
    
    # Generate batch of offline locations
    base_time = datetime.utcnow() - timedelta(minutes=10)
    locations = []
    
    for i in range(5):
        locations.append({
            "lat": 12.96 - (i * 0.002),
            "lng": 77.56 + (i * 0.002),
            "speed": 15 - i,
            "heading": 135 + (i * 5),
            "captured_at": (base_time + timedelta(seconds=i*30)).isoformat()
        })
    
    success, data = api_call("POST", f"/truck/{truck_id}/sync", {"locations": locations})
    if success:
        print_success(f"Synced {data.get('synced', 0)} locations")
        return True
    else:
        print_error(f"Offline sync failed: {data}")
        return False


def test_truck_approach_simulation(truck_id: int, user_id: int):
    """
    Simulate truck approaching user's home.
    Tests alert system at different distances.
    """
    print_subheader("Simulating Truck Approach")
    
    print_info("Sending truck locations and monitoring alerts...")
    print()
    
    for i, loc in enumerate(TRUCK_ROUTE):
        # Send location
        success = test_send_location(
            truck_id, 
            loc["lat"], 
            loc["lng"], 
            loc["speed"], 
            loc["heading"]
        )
        
        if not success:
            continue
        
        # Get tracking data
        tracking = test_tracking(user_id)
        if not tracking:
            continue
        
        # Display status
        distance = tracking.get("distance", {})
        eta = tracking.get("eta", {})
        status = tracking.get("status", "unknown")
        alert = tracking.get("alert")
        
        # Status emoji
        status_emoji = {
            "approaching": "🚛",
            "arriving": "🚛💨",
            "here": "🚛✅",
            "passed": "🚛➡️",
            "offline": "⚪"
        }.get(status, "❓")
        
        print(f"  {i+1}. {status_emoji} Status: {status.upper()}")
        print(f"     📍 Distance: {distance.get('text', 'N/A')}")
        print(f"     ⏱️  ETA: {eta.get('text', 'N/A')}")
        
        # Check for alert
        if alert and alert.get("should_alert"):
            print(f"     {Colors.YELLOW}🔔 ALERT: {alert.get('message')}{Colors.END}")
            if alert.get("play_sound"):
                print(f"     {Colors.YELLOW}🔊 PLAY SOUND!{Colors.END}")
        
        print()
        time.sleep(0.5)  # Small delay between updates


def test_debug_database() -> bool:
    """Test debug endpoint"""
    print_subheader("Database Debug")
    
    success, data = api_call("GET", "/debug/db")
    if success:
        print_success("Database state:")
        print(f"\n  Zones ({len(data.get('zones', []))}):")
        for z in data.get('zones', []):
            print(f"    - {z}")
        print(f"\n  Trucks ({len(data.get('trucks', []))}):")
        for t in data.get('trucks', []):
            print(f"    - {t}")
        print(f"\n  Users ({len(data.get('users', []))}):")
        for u in data.get('users', []):
            print(f"    - {u}")
        return True
    else:
        print_warning("Debug endpoint not available (add it to main.py)")
        return False


# ============ MAIN TEST RUNNER ============

def run_all_tests():
    """Run complete test suite"""
    
    print_header("🚛 GARBAGE TRUCK TRACKER - API TEST SUITE")
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # ========== PHASE 1: HEALTH CHECK ==========
    print_header("PHASE 1: Server Health")
    
    if not test_health_check():
        print_error("Server is not running! Start it with:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return
    results["passed"] += 1
    
    # ========== PHASE 2: ZONE MANAGEMENT ==========
    print_header("PHASE 2: Zone Management")
    
    zone_id = test_create_zone()
    if zone_id:
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Cannot continue without zone")
        return
    
    if test_list_zones():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== PHASE 3: TRUCK MANAGEMENT ==========
    print_header("PHASE 3: Truck Management")
    
    truck_id = test_create_truck(zone_id)
    if truck_id:
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Cannot continue without truck")
        return
    
    if test_list_trucks():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== PHASE 4: DRIVER APP ==========
    print_header("PHASE 4: Driver App Endpoints")
    
    driver_data = test_driver_login(TEST_TRUCK["driver_phone"])
    if driver_data:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    if test_start_duty(truck_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== PHASE 5: USER MANAGEMENT ==========
    print_header("PHASE 5: User Management")
    
    user_id = test_register_user()
    if user_id:
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Cannot continue without user")
        return
    
    # Update home to ensure zone assignment
    if test_update_user_home(user_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    if test_update_user_settings(user_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    user_data = test_user_login(TEST_USER["phone"])
    if user_data:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== PHASE 6: LOCATION TRACKING ==========
    print_header("PHASE 6: Location Tracking")
    
    print_subheader("Send Initial Location")
    if test_send_location(truck_id, 12.96, 77.56, 20, 135):
        print_success("Location sent")
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    print_subheader("Track Truck")
    tracking = test_tracking(user_id)
    if tracking:
        print_success("Tracking data received:")
        print(f"  Status: {tracking.get('status')}")
        print(f"  Distance: {tracking.get('distance', {}).get('text', 'N/A')}")
        print(f"  ETA: {tracking.get('eta', {}).get('text', 'N/A')}")
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== PHASE 7: ALERT SIMULATION ==========
    print_header("PHASE 7: Alert Simulation")
    
    test_truck_approach_simulation(truck_id, user_id)
    results["passed"] += 1  # Simulation always "passes"
    
    # ========== PHASE 8: ADDITIONAL ENDPOINTS ==========
    print_header("PHASE 8: Additional Endpoints")
    
    if test_route_history(user_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    if test_nearby_trucks(TEST_USER["home_lat"], TEST_USER["home_lng"]):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    if test_zone_status(zone_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== PHASE 9: OFFLINE SYNC ==========
    print_header("PHASE 9: Offline Sync")
    
    if test_offline_sync(truck_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== PHASE 10: CLEANUP ==========
    print_header("PHASE 10: Cleanup & Debug")
    
    test_debug_database()
    
    if test_stop_duty(truck_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========== RESULTS ==========
    print_header("TEST RESULTS")
    
    total = results["passed"] + results["failed"] + results["skipped"]
    
    print(f"  {Colors.GREEN}✅ Passed: {results['passed']}{Colors.END}")
    print(f"  {Colors.RED}❌ Failed: {results['failed']}{Colors.END}")
    print(f"  {Colors.YELLOW}⏭️  Skipped: {results['skipped']}{Colors.END}")
    print(f"  📊 Total: {total}")
    print()
    
    if results["failed"] == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  Some tests failed. Check the output above.{Colors.END}")


# ============ ENTRY POINT ============

if __name__ == "__main__":
    # Parse command line arguments
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    if "--base-url" in sys.argv:
        idx = sys.argv.index("--base-url")
        if idx + 1 < len(sys.argv):
            BASE_URL = sys.argv[idx + 1]
    
    if "--reset" in sys.argv:
        db_file = "garbage_tracker.db"
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Deleted {db_file}")
    
    # Run tests
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)