## File Structure 
tracking-service/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── router.py
│   │       ├── trucks.py
│   │       ├── users.py
│   │       ├── tracking.py
│   │       └── websocket.py
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   └── db/
│
├── alembic/
│   └── versions/
│
├── tests/
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
