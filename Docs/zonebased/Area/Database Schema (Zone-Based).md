╔══════════════════════════════════════════════════════════════════════════════╗
║                    DATABASE SCHEMA (ZONE/AREA BASED)                          ║
╚══════════════════════════════════════════════════════════════════════════════╝


┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: zones                                                                   │
│  Description: Service areas/wards in the city                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  name            VARCHAR(100)        "Ward 5", "Sector 12", "HSR Layout"        │
│  city            VARCHAR(100)        "Bangalore"                                │
│                                                                                 │
│  -- Boundary of the zone (rectangle for simplicity) --                          │
│  min_lat         FLOAT               Southwest corner latitude                  │
│  max_lat         FLOAT               Northeast corner latitude                  │
│  min_lng         FLOAT               Southwest corner longitude                 │
│  max_lng         FLOAT               Northeast corner longitude                 │
│                                                                                 │
│  -- OR use center + radius for circular zone --                                 │
│  center_lat      FLOAT               Center point latitude                      │
│  center_lng      FLOAT               Center point longitude                     │
│  radius_km       FLOAT               Zone radius in km                          │
│                                                                                 │
│  -- Schedule info --                                                            │
│  typical_start   TIME                "06:30" - When truck usually starts        │
│  typical_end     TIME                "12:00" - When truck usually finishes      │
│                                                                                 │
│  is_active       BOOLEAN             Is this zone currently serviced?           │
│  created_at      DATETIME                                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ 1:1 (One truck per zone)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: trucks                                                                  │
│  Description: Garbage trucks                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  vehicle_number  VARCHAR(20) UNIQUE  "KA01AB1234"                               │
│  name            VARCHAR(100)        "Truck 1" (optional friendly name)         │
│                                                                                 │
│  -- Assigned zone --                                                            │
│  zone_id         INTEGER FK -> zones.id                                         │
│                                                                                 │
│  -- Driver info --                                                              │
│  driver_name     VARCHAR(100)                                                   │
│  driver_phone    VARCHAR(20) UNIQUE  Used for driver app login                  │
│                                                                                 │
│  -- Current status --                                                           │
│  is_active       BOOLEAN             Is truck on duty RIGHT NOW?                │
│  duty_started_at DATETIME            When driver pressed START today            │
│                                                                                 │
│  -- Latest location (cached for fast access) --                                 │
│  last_lat        FLOAT                                                          │
│  last_lng        FLOAT                                                          │
│  last_speed      FLOAT               km/h                                       │
│  last_heading    FLOAT               0-360 degrees                              │
│  last_update     DATETIME                                                       │
│                                                                                 │
│  created_at      DATETIME                                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ 1:N (Location history)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: truck_locations                                                         │
│  Description: GPS history for route display                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  truck_id        INTEGER FK -> trucks.id                                        │
│                                                                                 │
│  latitude        FLOAT                                                          │
│  longitude       FLOAT                                                          │
│  speed           FLOAT                                                          │
│  heading         FLOAT                                                          │
│                                                                                 │
│  captured_at     DATETIME            When GPS captured on device                │
│  synced_at       DATETIME            When server received it                    │
│  is_offline_sync BOOLEAN             Was this from offline queue?               │
│                                                                                 │
│  INDEX: (truck_id, captured_at)                                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: users                                                                   │
│  Description: Residents who track trucks                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  name            VARCHAR(100)                                                   │
│  phone           VARCHAR(20) UNIQUE                                             │
│                                                                                 │
│  -- Home location --                                                            │
│  home_lat        FLOAT                                                          │
│  home_lng        FLOAT                                                          │
│  home_address    VARCHAR(500)        "123, 5th Cross, HSR Layout"               │
│                                                                                 │
│  -- Auto-assigned zone based on home location --                                │
│  zone_id         INTEGER FK -> zones.id                                         │
│                                                                                 │
│  -- Alert preferences --                                                        │
│  alert_enabled   BOOLEAN DEFAULT true                                           │
│  alert_distance  INTEGER DEFAULT 500  Notify when truck is X meters away        │
│  alert_type      VARCHAR(20)          "push" / "missed_call" / "both"           │
│                                                                                 │
│  -- For push notifications --                                                   │
│  fcm_token       TEXT                                                           │
│                                                                                 │
│  created_at      DATETIME                                                       │
│  is_active       BOOLEAN                                                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ 1:N (Alert history)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: alerts_sent                                                             │
│  Description: Track sent alerts (avoid duplicates)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  user_id         INTEGER FK -> users.id                                         │
│  truck_id        INTEGER FK -> trucks.id                                        │
│                                                                                 │
│  alert_date      DATE                One alert per type per day                 │
│  alert_type      VARCHAR(20)         "approaching" / "arrived"                  │
│  sent_at         DATETIME                                                       │
│                                                                                 │
│  distance_meters INTEGER             How far was truck when alert sent          │
│                                                                                 │
│  UNIQUE: (user_id, truck_id, alert_date, alert_type)                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


══════════════════════════════════════════════════════════════════════════════
RELATIONSHIPS DIAGRAM
══════════════════════════════════════════════════════════════════════════════

    ┌──────────┐
    │  ZONES   │
    └────┬─────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌───────┐
│TRUCKS │  │ USERS │
│(1 per │  │(many  │
│ zone) │  │ per   │
└───┬───┘  │ zone) │
    │      └───┬───┘
    │          │
    ▼          ▼
┌────────┐  ┌────────┐
│LOCATION│  │ ALERTS │
│HISTORY │  │  SENT  │
└────────┘  └────────┘