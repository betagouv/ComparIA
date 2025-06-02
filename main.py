# Standard library imports
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Third-party imports
import gradio as gr
import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JsonWebKey
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

# Local imports
from languia import config
from languia.block_arena import demo
from languia.reveal import size_desc, license_desc, license_attrs
from languia.utils import get_gauge_count

# Load environment variables
load_dotenv()

# Log application startup info
logging.info("🚀 Starting ComparIA application")
logging.info(f"🐛 Debug mode: {config.debug}")
logging.info(f"🗄️  Database configured: {'Yes' if os.getenv('COMPARIA_DB_URI') else 'No'}")
logging.info(f"📁 Log directory: {os.getenv('LOGDIR', 'Not configured')}")

# Import Docs authentication module if available
try:
    from languia.docs_auth import DocsAPIClient
    docs_auth_available = True
except ImportError:
    docs_auth_available = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "your-session-secret"))

# Initialize OAuth
oauth = OAuth()

# Register the OpenID Connect provider
oauth.register(
    name='oidc',
    client_id=os.getenv("OIDC_CLIENT_ID"),
    client_secret=os.getenv("OIDC_CLIENT_SECRET"),
    server_metadata_url=os.getenv("OIDC_DISCOVERY_URL"),
    client_kwargs={'scope': os.getenv("OIDC_SCOPES")},
)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
# app.mount("/arene/custom_components", StaticFiles(directory="custom_components"), name="custom_components")

templates = Jinja2Templates(directory="templates")

# TODO: use gr.set_static_paths(paths=["test/test_files/"])?
gr.set_static_paths(paths=[config.assets_absolute_path])
# broken... using path set up by fastapi instead
logging.info("Allowing assets absolute path: " + config.assets_absolute_path)

# Set authorization credentials
auth = None

# Clashes with hot reloading
# if not config.debug:
#     test_all_endpoints(config.controller_url)

demo = demo.queue(
    max_size=None,
    default_concurrency_limit=None,
    # default_concurrency_limit=40,
    # status_update_rate="auto",
    api_open=False,
)
# Should enable queue w/ mount_gradio_app: https://github.com/gradio-app/gradio/issues/8839
demo.run_startup_events()

objective = config.objective

@app.get('/login')
async def login(request: Request):
    logger.info("Redirecting to OIDC provider for user login... ")
    # Redirect to the OIDC provider for authentication
    redirect_uri = request.url_for('callback')
    logger.info(f"/login Redirect URI: {redirect_uri}")
    logger.info(f"Request base URL: {request.base_url}")
    logger.info(f"Request headers: {request.headers}")
    return await oauth.oidc.authorize_redirect(request, redirect_uri)

async def parse_jwt_userinfo(token):
    metadata= await oauth.oidc.load_server_metadata()
    logger.info("Fetching user info from OIDC provider...")
    resp = await oauth.oidc.get(metadata['userinfo_endpoint'], token=token)
    if resp.status_code != 200:
        raise Exception("Failed to fetch user info from OIDC provider")
    logger.info("User info fetched successfully from OIDC provider.")
    user_info_jwt  = resp.text
    logger.info(f"User info JWT: {user_info_jwt}")

    # get keys
    keys = await oauth.oidc.get(metadata['jwks_uri'], token=token)
    if keys.status_code != 200:
        raise Exception("Failed to fetch JWKS from OIDC provider")
    keys_set = JsonWebKey.import_key_set(keys.json())
    logger.info("JWKS keys fetched successfully from OIDC provider.")

    #Decode the JWT
    logger.info("Decoding JWT user information...")
    claims = jwt.decode(
        user_info_jwt,
        keys_set
    )
    claims.validate()
    return claims

@app.get('/callback')
async def callback(request: Request):
    logger.info("/auth Handling OIDC authentication response...")
    try:
        logger.info("Request query params: %s", request.query_params)
        logger.info("Request URL: %s", request.url)
        token = await oauth.oidc.authorize_access_token(request)
        logger.info("/auth Get token...")
        logger.info("Token type: %s", token.get('token_type'))
        logger.info("Token expires in: %s", token.get('expires_in'))
        user = await parse_jwt_userinfo(token)
        logger.info("/auth User info: %s", user)
        request.session['user'] = dict(user)
        return RedirectResponse(url='/arene')
    except Exception as e:
        logger.error("Error in callback: %s", str(e))
        logger.error("Error type: %s", type(e))
        import traceback
        logger.error("Full traceback:\n%s", traceback.format_exc())
        raise

@app.get('/logout')
def logout(request: Request):
    logger.info("Logging out user and clearing session...")
    request.session.pop('user', None)
    return RedirectResponse(url='/')

app = gr.mount_gradio_app(
    app,
    demo,
    path="/arene",
    root_path="/arene",
    # allowed_paths=[config.assets_absolute_path],
    allowed_paths=[
        config.assets_absolute_path,
        "/tmp",
        "/tmp/gradio",
        "custom_components",
    ],
    show_error=config.debug,
)

favicon_path="assets/favicon/favicon.ico"

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    gauge_count = get_gauge_count()
    gauge_count_ratio = str(int(100 * get_gauge_count() / objective))
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": config,
            "gauge_count_ratio": gauge_count_ratio,
            "gauge_count": gauge_count,
            "objective": objective,
        },
    )


@app.get("/modeles", response_class=HTMLResponse)
async def models(request: Request):
    return templates.TemplateResponse(
        "models.html",
        {
            "title": "Liste des modèles",
            "request": request,
            "config": config,
            "models": config.models_extra_info,
            "size_desc": size_desc,
            "license_desc": license_desc,
            "license_attrs": license_attrs,
        },
    )


@app.get("/share", response_class=HTMLResponse)
async def share(i: str, request: Request):

    from languia.config import all_models_extra_info_toml

    try:
        import base64, json

        decoded = base64.b64decode(i)
    
        data = json.loads(decoded)
        assert data.get("a") in all_models_extra_info_toml
        model_a_name = data.get("a")
        assert data.get("b") in all_models_extra_info_toml
        model_b_name = data.get("b")
        assert isinstance(data.get("ta"), int)
        model_a_tokens = data.get("ta")
        assert isinstance(data.get("tb"), int)
        model_b_tokens = data.get("tb")
        assert data.get("c") in ["a", "b"] or data.get("c") == None
        if data.get("c") == "a":
            chosen_model = "model-a"
        elif data.get("c") == "b":
            chosen_model = "model-b"
        else:
            chosen_model = None
    except:
        return FileResponse("templates/50x.html", status_code=500)

    from languia.utils import build_model_extra_info

    model_a = build_model_extra_info(model_a_name, all_models_extra_info_toml)
    model_b = build_model_extra_info(model_b_name, all_models_extra_info_toml)

    from languia.reveal import (
        get_llm_impact,
        calculate_lightbulb_consumption,
        calculate_streaming_hours,
        convert_range_to_value,
    )

    model_a_impact = get_llm_impact(model_a, model_a_name, model_a_tokens, None)
    model_b_impact = get_llm_impact(model_b, model_b_name, model_b_tokens, None)

    model_a_kwh = convert_range_to_value(model_a_impact.energy.value)
    model_b_kwh = convert_range_to_value(model_b_impact.energy.value)
    model_a_co2 = convert_range_to_value(model_a_impact.gwp.value)
    model_b_co2 = convert_range_to_value(model_b_impact.gwp.value)
    lightbulb_a, lightbulb_a_unit = calculate_lightbulb_consumption(model_a_kwh)
    lightbulb_b, lightbulb_b_unit = calculate_lightbulb_consumption(model_b_kwh)

    streaming_a, streaming_a_unit = calculate_streaming_hours(model_a_co2)
    streaming_b, streaming_b_unit = calculate_streaming_hours(model_b_co2)

    return templates.TemplateResponse(
        "share.html",
        {
            "b64": i,
            "title": "Mon bilan",
            "model_a": model_a,
            "model_b": model_b,
            "chosen_model": chosen_model,
            "model_a_kwh": model_a_kwh,
            "model_b_kwh": model_b_kwh,
            "model_a_co2": model_a_co2,
            "model_b_co2": model_b_co2,
            "size_desc": size_desc,
            "license_desc": license_desc,
            "license_attrs": license_attrs,
            "model_a_tokens": model_a_tokens,
            "model_b_tokens": model_b_tokens,
            "streaming_a": streaming_a,
            "streaming_a_unit": streaming_a_unit,
            "streaming_b": streaming_b,
            "streaming_b_unit": streaming_b_unit,
            "lightbulb_a": lightbulb_a,
            "lightbulb_a_unit": lightbulb_a_unit,
            "lightbulb_b": lightbulb_b,
            "lightbulb_b_unit": lightbulb_b_unit,
            "request": request,
            "config": config,
            "models": config.models_extra_info,
            "size_desc": size_desc,
            "license_desc": license_desc,
            "license_attrs": license_attrs,
        },
    )


@app.get("/a-propos", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {
            "title": "À propos",
            "request": request,
            "config": config,
        },
    )


@app.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    return templates.TemplateResponse(
        "faq.html",
        {
            "title": "Vos questions les plus courantes",
            "request": request,
            "config": config,
        },
    )


@app.get("/partenaires", response_class=HTMLResponse)
async def partners(request: Request):
    return templates.TemplateResponse(
        "partners.html",
        {
            "title": "Partenaires",
            "request": request,
            "config": config,
        },
    )


@app.get("/mentions-legales", response_class=HTMLResponse)
async def legal(request: Request):
    return templates.TemplateResponse(
        "legal.html",
        {
            "title": "Mentions légales",
            "request": request,
            "config": config,
        },
    )


@app.get("/donnees-personnelles", response_class=HTMLResponse)
async def policy(request: Request):
    return templates.TemplateResponse(
        "policy.html",
        {
            "title": "Politique de confidentialité",
            "request": request,
            "config": config,
        },
    )


@app.get("/modalites", response_class=HTMLResponse)
async def tos(request: Request):
    return templates.TemplateResponse(
        "tos.html",
        {
            "title": "Modalités d'utilisation",
            "request": request,
            "config": config,
            "models": config.models_extra_info,
        },
    )


@app.get("/accessibilite", response_class=HTMLResponse)
async def accessibility(request: Request):
    return templates.TemplateResponse(
        "accessibility.html",
        {
            "title": "Déclaration d'accessibilité",
            "request": request,
            "config": config,
        },
    )


@app.get("/bnf", response_class=HTMLResponse)
async def bnf(request: Request):
    return templates.TemplateResponse(
        "bnf.html",
        {
            "title": "Conférences",
            "request": request,
            "config": config,
        },
    )


# Docs integration endpoints (if docs_auth module is available)
if docs_auth_available:
    from fastapi.responses import RedirectResponse
    logging.info("✅ Docs integration module loaded successfully")
    logging.info(f"📋 Docs API Base URL: {os.getenv('DOCS_API_BASE_URL', 'Not configured')}")
    if os.getenv("DOCS_API_TOKEN"):
        logging.info("🔑 Docs API token is configured")
    else:
        logging.warning("⚠️  Docs API token is NOT configured - Docs integration will not work")
else:
    logging.warning("❌ Docs integration module not available - check dependencies")
    
    # Provide fallback routes when docs_auth is not available
    @app.get("/docs/connect")
    @app.get("/docs/documents") 
    async def docs_not_available(request: Request):
        logging.error("🚫 Docs integration accessed but module not available")
        return templates.TemplateResponse(
            "50x.html", 
            {"request": request, "config": config}, 
            status_code=503
        )

if docs_auth_available:
    @app.get("/docs/connect")
    async def docs_connect(request: Request, token: str = None):
        """Connect to Docs with API token"""
        logging.info(f"📥 Docs connect request from IP: {request.client.host}")
        if not token:
            logging.info("🔐 Showing Docs connection form")
            # Show the connection form
            return templates.TemplateResponse(
                "docs_connect.html",
                {
                    "title": "Connecter Docs",
                    "request": request,
                    "config": config,
                },
            )
        
        # Just store the token and redirect
        logging.info(f"🔑 Storing Docs token and redirecting to documents page")
        response = RedirectResponse(url="/docs/documents")
        response.set_cookie(
            key="docs_token",
            value=token,
            max_age=3600,  # 1 hour
            httponly=True,
            secure=True,
            samesite="lax"
        )
        return response
    
    @app.get("/docs/documents", response_class=HTMLResponse)
    async def docs_documents(request: Request):
        """Docs documents page"""
        import os
        
        logging.info(f"📄 Docs documents request from IP: {request.client.host}")
        
        # Get token from cookie or environment
        docs_token = None
        if hasattr(request, 'cookies') and 'docs_token' in request.cookies:
            docs_token = request.cookies['docs_token']
            logging.info("🍪 Using Docs token from cookie")
        elif os.getenv("DOCS_API_TOKEN"):
            docs_token = os.getenv("DOCS_API_TOKEN")
            logging.info("🔧 Using Docs token from environment variable")
        
        if not docs_token:
            logging.warning("❌ No Docs token available - redirecting to connect page")
            return templates.TemplateResponse(
                "docs_connect.html",
                {
                    "title": "Connecter Docs",
                    "request": request,
                    "config": config,
                },
            )
        
        # Get Docs API client
        try:
            docs_client = DocsAPIClient(api_token=docs_token)
            logging.info("✅ Docs API client initialized successfully")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Docs API client: {e}")
            error = f"Configuration error: {e}"
            documents = []
        else:
            try:
                logging.info("🔄 Fetching documents from Docs API...")
                # Fetch documents from Docs
                documents = await docs_client.list_documents()
                logging.info(f"✅ Successfully fetched {len(documents)} documents")
                error = None
            except Exception as e:
                logging.error(f"❌ Failed to fetch documents from Docs API: {e}")
                documents = []
                error = str(e)
        
        return templates.TemplateResponse(
            "docs_documents.html",
            {
                "title": "Documents Docs",
                "request": request,
                "config": config,
                "documents": documents,
                "error": error,
            },
        )
    
    @app.get("/docs/logout")
    async def docs_logout(request: Request):
        """Logout from Docs"""
        response = RedirectResponse(url="/")
        response.delete_cookie("docs_token")
        return response
    
    @app.get("/docs/api/documents")
    async def api_list_docs(request: Request):
        """API endpoint to list Docs documents"""
        import os
        from fastapi import HTTPException
        
        # Get token from cookie or environment
        docs_token = None
        if hasattr(request, 'cookies') and 'docs_token' in request.cookies:
            docs_token = request.cookies['docs_token']
        elif os.getenv("DOCS_API_TOKEN"):
            docs_token = os.getenv("DOCS_API_TOKEN")
            
        if not docs_token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        docs_client = DocsAPIClient(api_token=docs_token)
        documents = await docs_client.list_documents()
        return {"documents": documents}


@app.exception_handler(500)
async def http_exception_handler(request, exc):
    return FileResponse("templates/50x.html", status_code=500)


@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request, exc):
    return templates.TemplateResponse(
        "404.html",
        {"title": "Page non trouvée", "request": request, "config": config},
        status_code=404,
    )
