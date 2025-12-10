#!/bin/bash
# Run backend server

cd backend

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python3 app.py

