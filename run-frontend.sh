#!/bin/bash
# Run frontend development server

cd frontend

if [ ! -d "node_modules" ]; then
    echo "❌ Node modules not found. Run ./setup.sh first."
    exit 1
fi

npm run dev

