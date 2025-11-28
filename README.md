<p align="center">
  <img src="https://img.icons8.com/color/96/garbage-truck.png" alt="Garbage Truck Tracker Logo"/>
</p>

<h1 align="center">🚛 Garbage Truck Tracker</h1>

<p align="center">
  <strong>Real-time garbage truck tracking system — Like "Where is my Train" but for garbage trucks!</strong>
</p>

<p align="center">
  <a href="https://github.com/Where-is-my-garbage-Truck/Where--is-my-truck-backend/blob/main/Docs">Features</a> •
  <a href="https://github.com/Where-is-my-garbage-Truck/Where--is-my-truck-backend/blob/main/Docs">Demo</a> •
  <a href="https://github.com/Where-is-my-garbage-Truck/Where--is-my-truck-backend/blob/main/Docs">Installation</a> •
  <a href="https://github.com/Where-is-my-garbage-Truck/Where--is-my-truck-backend/blob/main/Docs/API%20Endpoints%20Design.md">API Docs</a> •
  <a href="https://github.com/Where-is-my-garbage-Truck/Where--is-my-truck-backend/blob/main/Docs">Roadmap</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.0-blue.svg" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/fastapi-0.109+-teal.svg" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License"/>
  <img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"/>
</p>

---

## 📖 About

**Garbage Truck Tracker** is a complete solution for tracking garbage collection trucks in real-time. Residents can see exactly where the truck is, get ETA estimates, and receive alerts when the truck is approaching their home.

### The Problem
> "I never know when the garbage truck will come. Sometimes I miss it and have to wait another day."

### The Solution
A mobile-friendly tracking system that shows:
- 📍 Real-time truck location on map
- ⏱️ Accurate ETA to your home
- 🔔 Smart alerts when truck is near
- 📊 Route history and patterns

---

## ✨ Features

### For Residents (User App)
| Feature | Description |
|---------|-------------|
| 🗺️ **Live Tracking** | See truck location on map in real-time |
| 📏 **Distance & ETA** | Know exactly how far and how long |
| 🔔 **Smart Alerts** | Get notified when truck is 5 mins away |
| 🔊 **Sound Alerts** | Loud notification even if phone is silent |
| 📱 **Offline Support** | Works even with poor connectivity |

### For Drivers (Driver App)
| Feature | Description |
|---------|-------------|
| 🟢 **One-Tap Start** | Simple Start/Stop button |
| 📡 **Auto GPS** | Background location tracking |
| 📴 **Offline Mode** | Stores locations, syncs when online |
| 🔋 **Battery Efficient** | Optimized for all-day use |

### For Administrators
| Feature | Description |
|---------|-------------|
| 🏘️ **Zone Management** | Define service areas on map |
| 🚛 **Fleet Management** | Manage trucks and drivers |
| 📊 **Analytics** | Track coverage and efficiency |
| 👥 **User Management** | Manage resident accounts |

---

## 🏗️ System Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Driver App    │         │    User App     │
│  (Send GPS)     │         │  (Track Truck)  │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │    ┌───────────────┐      │
         └────►   FastAPI     ◄──────┘
              │   Backend     │
              └───────┬───────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Database │ │  Google  │ │ Firebase │
   │ SQLite/  │ │   Maps   │ │   FCM    │
   │ Postgres │ │   API    │ │  (Push)  │
   └──────────┘ └──────────┘ └──────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip (Python package manager)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/garbage-truck-tracker.git
cd garbage-truck-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Open API docs
open http://localhost:8000/docs
```

---

## 📁 Project Structure

```
garbage-truck-tracker/
├── 📂 app/
│   ├── 📂 routes/
│   │   ├── zones.py        # Zone management
│   │   ├── trucks.py       # Truck & driver endpoints
│   │   ├── users.py        # User management
│   │   ├── tracking.py     # Live tracking
│   │   └── websocket.py    # Real-time updates
│   ├── 📂 services/
│   │   ├── location.py     # Distance & ETA calculations
│   │   └── alerts.py       # Alert system
│   ├── config.py           # Configuration
│   ├── database.py         # Database connection
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   └── main.py             # FastAPI application
├── 📂 tests/
│   └── test_api.py         # Complete test suite
├── .env.example            # Environment template
├── requirements.txt        # Dependencies
└── README.md               # This file
```

---

## 🔌 API Documentation

### Base URL
```
http://localhost:8000
```

### Authentication
Currently uses phone-based login (no password). JWT auth planned for production.

### Main Endpoints

#### Zones (Admin)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/zones/` | Create zone |
| `GET` | `/zones/` | List zones |
| `GET` | `/zones/{id}` | Get zone details |
| `PUT` | `/zones/{id}` | Update zone |
| `DELETE` | `/zones/{id}` | Deactivate zone |

#### Trucks (Admin + Driver)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/truck/` | Create truck |
| `GET` | `/truck/all` | List trucks |
| `POST` | `/truck/login` | Driver login |
| `POST` | `/truck/{id}/start` | Start duty |
| `POST` | `/truck/{id}/stop` | Stop duty |
| `POST` | `/truck/{id}/location` | Send GPS |
| `POST` | `/truck/{id}/sync` | Sync offline |

#### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/user/register` | Register user |
| `POST` | `/user/login` | User login |
| `PUT` | `/user/{id}/settings` | Update settings |
| `PUT` | `/user/{id}/home` | Update home |

#### Tracking ⭐
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/track/{user_id}` | **Main tracking** |
| `GET` | `/track/{user_id}/route` | Route history |
| `GET` | `/track/nearby` | Find nearby trucks |
| `WS` | `/ws/track/{user_id}` | Real-time WebSocket |

### Example Response

```json
GET /track/1

{
  "truck": {
    "id": 1,
    "vehicle_number": "KA01AB1234",
    "is_active": true,
    "lat": 12.943,
    "lng": 77.595,
    "speed": 12.5,
    "last_update_seconds_ago": 5
  },
  "distance": {
    "meters": 450,
    "text": "450 m"
  },
  "eta": {
    "minutes": 3,
    "text": "~3 mins",
    "arrival_time": "06:48 AM"
  },
  "status": "arriving",
  "alert": {
    "should_alert": true,
    "alert_type": "arriving",
    "message": "🚛 Truck almost here! Only 450 m away!",
    "play_sound": true
  }
}
```

📚 **Full API Documentation:** http://localhost:8000/docs

---

## ⚙️ Configuration

### Environment Variables

```env
# App Settings
APP_NAME="Garbage Truck Tracker"
DEBUG=true

# Database (SQLite default, easy PostgreSQL switch)
DATABASE_URL=sqlite:///./garbage_tracker.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/garbage_tracker

# Alert Distances (meters)
ALERT_DISTANCE_APPROACHING=1000
ALERT_DISTANCE_ARRIVING=500
ALERT_DISTANCE_HERE=100

# Firebase Push Notifications (optional)
FCM_SERVER_KEY=your_firebase_server_key

# Google Maps (optional, for accurate ETA)
GOOGLE_MAPS_API_KEY=your_google_maps_key

# Missed Call Service (optional)
MISSED_CALL_API_KEY=your_api_key
MISSED_CALL_API_URL=https://api.provider.com/call
```

### Switching to PostgreSQL

```bash
# Install driver
pip install psycopg2-binary

# Update .env
DATABASE_URL=postgresql://user:password@localhost:5432/garbage_tracker

# Restart server (tables auto-created)
uvicorn app.main:app --reload
```

---

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
python tests/test_api.py

# With custom URL
python tests/test_api.py --base-url https://your-server.com

# Reset database first
python tests/test_api.py --reset
```

### Expected Output

```
============================================================
  🚛 GARBAGE TRUCK TRACKER - API TEST SUITE
============================================================

  ✅ Passed: 19
  ❌ Failed: 0
  📊 Total: 19

🎉 ALL TESTS PASSED!
```

---

## 🗺️ Roadmap

### ✅ Completed
- [x] Backend API (FastAPI)
- [x] Database models (SQLAlchemy)
- [x] Zone-based tracking
- [x] Real-time location updates
- [x] WebSocket support
- [x] Alert system (approaching/arriving/here)
- [x] Offline sync
- [x] Distance & ETA calculation
- [x] Complete test suite

### 🚧 In Progress
- [ ] Firebase Push Notifications
- [ ] Google Maps Integration (accurate ETA)

### 📋 Planned
- [ ] Driver Mobile App (Flutter)
- [ ] User Mobile App (Flutter)
- [ ] Admin Web Dashboard
- [ ] Docker deployment
- [ ] CI/CD pipeline

### 💡 Future Ideas
- [ ] Route optimization
- [ ] Pickup scheduling
- [ ] Analytics dashboard
- [ ] Multi-language support
- [ ] SMS notifications

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/garbage-truck-tracker.git

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests before committing
python tests/test_api.py
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by "Where is my Train" app
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Icons by [Icons8](https://icons8.com/)

---

## 📞 Support

- 📧 Email: randintrandom6@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/harhspalod/Where-is-my-garbage-Truck/Where--is-my-truck-backend/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/harhspalod/Where-is-my-garbage-Truck/Where--is-my-truck-backend/discussions)

---

<p align="center">
  Made with ❤️ for cleaner cities
</p>

<p align="center">
  <a href="#top">⬆️ Back to Top</a>
</p>
