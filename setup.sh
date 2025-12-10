#!/bin/bash
# Setup script for local deployment

echo "🚀 Setting up Tiered Email Filtering Web App..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    exit 1
fi

echo "✅ Python and Node.js found"

# Setup backend
echo ""
echo "📦 Setting up backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    if python3 -m venv venv 2>/dev/null; then
        source venv/bin/activate
    else
        echo "⚠️  Virtual environment creation failed. Using system Python."
        echo "   (This is okay if packages are already installed)"
    fi
fi

if [ -d "venv" ]; then
    source venv/bin/activate
fi

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✅ Backend dependencies installed"
cd ..

# Setup frontend
echo ""
echo "📦 Setting up frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi
echo "✅ Frontend dependencies installed"
cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the app:"
echo "  1. Start backend: ./run-backend.sh"
echo "  2. Start frontend: ./run-frontend.sh"
echo ""
echo "Or run both in separate terminals:"
echo "  Terminal 1: cd backend && source venv/bin/activate && python app.py"
echo "  Terminal 2: cd frontend && npm run dev"

