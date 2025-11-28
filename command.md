5. Run the server:
bash
uvicorn app.main:app --reload
6. Test it!

Open http://localhost:8000/docs for Swagger UI
Open http://localhost:8000/health for health check


🧪 Quick Test Commands
bash# Create a supervisor
curl -X POST http://localhost:8000/api/v1/supervisors/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Rajesh Kumar", "phone": "+919876543210"}'

# Start tracking session
curl -X POST http://localhost:8000/api/v1/tracking/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"supervisor_id": 1, "vehicle_identifier": "KA-01-AB-1234"}'

# Add GPS point
curl -X POST http://localhost:8000/api/v1/tracking/sessions/1/points \
  -H "Content-Type: application/json" \
  -d '{"latitude": 12.9716, "longitude": 77.5946, "timestamp": "2024-01-15T10:30:00Z"}'

# Get GPS trail
curl http://localhost:8000/api/v1/tracking/sessions/1/points

# Stop session
curl -X POST http://localhost:8000/api/v1/tracking/sessions/1/stop

s