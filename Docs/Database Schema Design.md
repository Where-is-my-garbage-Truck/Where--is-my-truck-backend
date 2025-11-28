╔══════════════════════════════════════════════════════════════════════════════╗
║                              DATABASE SCHEMA                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝


┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: trucks                                                                  │
│  Description: Garbage trucks with mounted phone                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  name            VARCHAR(100)        "Truck 1", "Zone A Truck"                  │
│  vehicle_number  VARCHAR(20) UNIQUE  "KA01AB1234"                               │
│  zone            VARCHAR(100)        "Sector 5", "Ward 12"                      │
│                                                                                 │
│  driver_name     VARCHAR(100)        Current driver name                        │
│  driver_phone    VARCHAR(20)         Driver's phone number                      │
│                                                                                 │
│  is_active       BOOLEAN             Is truck on duty RIGHT NOW?                │
│                                                                                 │
│  -- Cached latest location (for fast queries) --                                │
│  last_latitude   FLOAT                                                          │
│  last_longitude  FLOAT                                                          │
│  last_speed      FLOAT               km/h                                       │
│  last_heading    FLOAT               0-360 degrees                              │
│  last_update     DATETIME            When last location received                │
│                                                                                 │
│  created_at      DATETIME                                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ 1:N
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: truck_locations                                                         │
│  Description: Location history (for route display & analytics)                  │
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
│  captured_at     DATETIME            When GPS captured (on device)              │
│  synced_at       DATETIME            When received by server                    │
│  is_offline_sync BOOLEAN             Was this synced later?                     │
│                                                                                 │
│  INDEX: (truck_id, captured_at) -- For route queries                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: users                                                                   │
│  Description: Residents who want to track trucks                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  name            VARCHAR(100)                                                   │
│  phone           VARCHAR(20) UNIQUE   For missed call alerts                    │
│                                                                                 │
│  -- Home location (where they want truck alerts) --                             │
│  home_latitude   FLOAT                                                          │
│  home_longitude  FLOAT                                                          │
│  home_address    VARCHAR(500)         "123, Main Street, Sector 5"              │
│                                                                                 │
│  -- Which truck to track --                                                     │
│  truck_id        INTEGER FK -> trucks.id                                        │
│                                                                                 │
│  -- Alert preferences --                                                        │
│  alert_enabled   BOOLEAN DEFAULT true                                           │
│  alert_distance  INTEGER DEFAULT 500   Alert when truck is X meters away        │
│  alert_type      VARCHAR(20)           "push" / "missed_call" / "both"          │
│                                                                                 │
│  -- FCM token for push notifications --                                         │
│  fcm_token       VARCHAR(500)                                                   │
│                                                                                 │
│  created_at      DATETIME                                                       │
│  is_active       BOOLEAN                                                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ 1:N
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: user_alerts                                                             │
│  Description: Track which alerts were sent (avoid duplicate alerts)             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  user_id         INTEGER FK -> users.id                                         │
│  truck_id        INTEGER FK -> trucks.id                                        │
│                                                                                 │
│  alert_date      DATE                 Which day (one alert per day)             │
│  alert_type      VARCHAR(20)          "approaching" / "arrived" / "passed"      │
│  alert_sent_at   DATETIME                                                       │
│                                                                                 │
│  -- Location when alert was triggered --                                        │
│  truck_latitude  FLOAT                                                          │
│  truck_longitude FLOAT                                                          │
│  distance_meters INTEGER                                                        │
│                                                                                 │
│  UNIQUE: (user_id, truck_id, alert_date, alert_type)                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: zones (Optional - for multi-zone cities)                                │
│  Description: Define service areas                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  id              INTEGER PRIMARY KEY                                            │
│  name            VARCHAR(100)          "Sector 5", "HSR Layout"                 │
│  city            VARCHAR(100)          "Bangalore"                              │
│                                                                                 │
│  -- Bounding box for the zone --                                                │
│  min_latitude    FLOAT                                                          │
│  max_latitude    FLOAT                                                          │
│  min_longitude   FLOAT                                                          │
│  max_longitude   FLOAT                                                          │
│                                                                                 │
│  -- Typical schedule --                                                         │
│  typical_start   TIME                  "06:30"                                  │
│  typical_end     TIME                  "12:00"                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘