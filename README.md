## Backend file main code
``` bash
📦 garbage-tracker/
 ┣ 📂 app/
 ┃ ┣ 📂 routes/
 ┃ ┃ ┣ 📜 __init__.py
 ┃ ┃ ┣ 📜 zones.py          # Zone management (Admin)
 ┃ ┃ ┣ 📜 trucks.py         # Truck & Driver endpoints
 ┃ ┃ ┣ 📜 users.py          # User registration & settings
 ┃ ┃ ┣ 📜 tracking.py       # Live tracking endpoints
 ┃ ┃ ┗ 📜 websocket.py      # Real-time WebSocket
 ┃ ┣ 📂 services/
 ┃ ┃ ┣ 📜 __init__.py
 ┃ ┃ ┣ 📜 location.py       # Distance, ETA calculations
 ┃ ┃ ┗ 📜 alerts.py         # Alert checking & sending
 ┃ ┣ 📜 __init__.py
 ┃ ┣ 📜 config.py           # Configuration management
 ┃ ┣ 📜 database.py         # Database connection
 ┃ ┣ 📜 models.py           # SQLAlchemy models
 ┃ ┣ 📜 schemas.py          # Pydantic schemas
 ┃ ┗ 📜 main.py             # FastAPI application
 ┣ 📜 .env                   # Environment variables
 ┣ 📜 .env.example           # Example env file
 ┣ 📜 requirements.txt       # Dependencies
 ┗ 📜 README.md              # Documentation
 ```

 ## All about the documentation
``` bash
📦Docs
 ┣ 📂zonebased
 ┃ ┗ 📂Area
 ┃ ┃ ┣ 📜API Endpoints (Zone-Based).md
 ┃ ┃ ┣ 📜Database Schema (Zone-Based).md
 ┃ ┃ ┣ 📜User Flow (Zone-Based).md
 ┃ ┃ ┗ 📜Zone Based System.md
 ┣ 📜API Endpoints Design.md
 ┣ 📜Data Flow Diagram.md
 ┣ 📜Database Schema Design.md
 ┣ 📜Google Maps Integration Plan.md
 ┣ 📜Notification System Design.md
 ┣ 📜System Architecture Diagram.md
 ┗ 📜project_status.md
 ```


## All the test

``` bash 
📦tests
 ┣ 📜__init__.py
 ┣ 📜test_api.py
 ┗ 📜test_quick.sh
 ```

 ## setup 
 ```bash 
python3 -m venv env
or 
virtualenv env (Avoid it)
```

## after it 
``` bash
source env/bin/activate
pip install -r requirements.txt
```

## start
``` bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 (dont change the directory)
```

## check the work done and left at the work folder
``` bash
📦work
 ┗ 📜phase1.md
 ```





