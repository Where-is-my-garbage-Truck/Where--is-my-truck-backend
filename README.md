## Backend file main code
``` bash
📦app
 ┣ 📂__pycache__
 ┃ ┣ 📜__init__.cpython-310.pyc
 ┃ ┣ 📜database.cpython-310.pyc
 ┃ ┣ 📜main.cpython-310.pyc
 ┃ ┣ 📜models.cpython-310.pyc
 ┃ ┗ 📜schemas.cpython-310.pyc
 ┣ 📂routes
 ┃ ┣ 📂__pycache__
 ┃ ┃ ┣ 📜__init__.cpython-310.pyc
 ┃ ┃ ┣ 📜drivers.cpython-310.pyc
 ┃ ┃ ┣ 📜tracking.cpython-310.pyc
 ┃ ┃ ┗ 📜users.cpython-310.pyc
 ┃ ┣ 📜__init__.py
 ┃ ┣ 📜drivers.py
 ┃ ┣ 📜tracking.py
 ┃ ┗ 📜users.py
 ┣ 📜__init__.py
 ┣ 📜database.py
 ┣ 📜main.py
 ┣ 📜models.py
 ┗ 📜schemas.py
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
 ┗ 📜System Architecture Diagram.md
 ```


## All the test

``` bash 
📦tests
 ┗ 📜__init__.py
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





