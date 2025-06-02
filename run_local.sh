#!/bin/bash

# compar:IA Local Run Script

echo "🚀 Starting compar:IA in local mode..."

# Set environment variables
export LANGUIA_DEBUG=True
export LOGDIR="./data"

# Load .env file if it exists
if [ -f .env ]; then
    echo "📄 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create log directory if it doesn't exist
mkdir -p ./data

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import gradio" 2>/dev/null; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if custom components are built
if [ ! -d "custom_components/frinput/dist" ]; then
    echo "🔨 Building custom components..."
    echo "  - Building FrInput..."
    gradio cc install custom_components/frinput
    gradio cc build --no-generate-docs custom_components/frinput
    
    echo "  - Building CustomRadioCard..."
    gradio cc install custom_components/customradiocard
    gradio cc build --no-generate-docs custom_components/customradiocard
    
    echo "  - Building CustomDropdown..."
    gradio cc install custom_components/customdropdown
    gradio cc build --no-generate-docs custom_components/customdropdown
    
    echo "  - Building CustomChatbot..."
    gradio cc install custom_components/customchatbot
    cd custom_components/customchatbot/frontend && npm install @gouvfr/dsfr && cd ../../..
    gradio cc build --no-generate-docs custom_components/customchatbot
fi

# Start the application
echo "✅ Starting application on http://localhost:8000"
echo "   - Main site: http://localhost:8000"
echo "   - Arena: http://localhost:8000/arene"
echo "   - Models: http://localhost:8000/modeles"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn main:app --reload --timeout-graceful-shutdown 1