# compar:IA Local Setup Guide

This guide will help you run compar:IA locally on your machine without API keys (for testing purposes).

## Prerequisites

- Python 3.11 or higher
- PostgreSQL (optional, for full functionality)
- Node.js and npm (for building custom Gradio components)

## Step 1: Clone and Setup Environment

```bash
# Navigate to your project directory
cd /Users/simonaszilinskas/ComparIA

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Build Custom Gradio Components

compar:IA uses custom Gradio components that need to be built:

```bash
# Install and build FrInput component
gradio cc install custom_components/frinput
gradio cc build --no-generate-docs custom_components/frinput

# Install and build CustomRadioCard component
gradio cc install custom_components/customradiocard
gradio cc build --no-generate-docs custom_components/customradiocard

# Install and build CustomDropdown component
gradio cc install custom_components/customdropdown
gradio cc build --no-generate-docs custom_components/customdropdown

# Install and build CustomChatbot component (includes DSFR dependencies)
gradio cc install custom_components/customchatbot
npm install @gouvfr/dsfr
gradio cc build --no-generate-docs custom_components/customchatbot
```

## Step 3: Configure API Endpoints (Mock Setup)

Since we're running without API keys, create a basic configuration:

```bash
# Copy the distribution file
cp register-api-endpoint-file.json.dist register-api-endpoint-file.json
```

Edit `register-api-endpoint-file.json` to add a mock model configuration:

```json
[
    {
        "api_id": "mock-model",
        "model_id": "mock-model",
        "api_base": "http://localhost:8000/v1/",
        "api_type": "openai",
        "api_key": "mock-key",
        "model_name": "Mock Model",
        "recommended_config": {
            "temperature": 0.7
        }
    }
]
```

## Step 4: Set Environment Variables

Create a `.env` file or export these variables:

```bash
# Enable debug mode
export LANGUIA_DEBUG=True

# Optional: Database configuration (if you have PostgreSQL)
# export COMPARIA_DB_URI="postgresql://user:password@localhost/comparia"

# Optional: Set log directory
export LOGDIR="./data"

# Optional: Controller URL (for distributed setup)
# export LANGUIA_CONTROLLER_URL="http://localhost:21001"
```

## Step 5: Database Setup (Optional)

If you want to use PostgreSQL for logging and storing conversations:

```bash
# Create database
createdb comparia

# Run schema files
psql -d comparia -f schemas/conversations.sql
psql -d comparia -f schemas/logs.sql
psql -d comparia -f schemas/reactions.sql
psql -d comparia -f schemas/votes.sql
```

## Step 6: Run the Application

### Option A: Using Uvicorn (Recommended)

```bash
# Run with auto-reload for development
uvicorn main:app --reload --timeout-graceful-shutdown 1

# Or run in production mode
uvicorn main:app
```

The application will be available at: http://localhost:8000

### Option B: Using Gradio directly (Arena only)

```bash
gradio demo.py
```

## Step 7: Access the Application

- Main site: http://localhost:8000
- Arena: http://localhost:8000/arene
- Models list: http://localhost:8000/modeles
- About: http://localhost:8000/a-propos

## Troubleshooting

### Issue: Custom components not loading
- Make sure all custom components are built successfully
- Check that npm dependencies are installed

### Issue: No models available
- Verify `register-api-endpoint-file.json` exists and contains valid model configurations
- Check logs in the `./data` directory if LOGDIR is set

### Issue: Database connection errors
- Ensure PostgreSQL is running
- Verify database credentials in COMPARIA_DB_URI
- Check that schemas are properly created

## Next Steps

To add real AI models:
1. Obtain API keys from providers (OpenAI, Anthropic, etc.)
2. Update `register-api-endpoint-file.json` with real API configurations
3. Set appropriate API keys in the configuration

## Development Mode Features

When `LANGUIA_DEBUG=True`:
- More detailed error messages
- Auto-reload on code changes
- Debug logging enabled

## Notes

- The application uses the French Design System (DSFR)
- Custom CSS and JavaScript are loaded from the `assets/` directory
- Templates use Jinja2 and are located in `templates/`
- Gradio components are customized using Svelte