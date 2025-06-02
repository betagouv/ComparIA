"""
Docs authentication and API client
"""
import os
import secrets
import base64
import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import httpx
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)

# Configuration from environment
DOCS_API_BASE_URL = os.getenv("DOCS_API_BASE_URL", "https://docs-ia.beta.numerique.gouv.fr/api/v1.0")
DOCS_API_TOKEN = os.getenv("DOCS_API_TOKEN", "")  # User API token

# Session configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))
SESSION_DURATION = int(os.getenv("SESSION_DURATION", "3600"))  # 1 hour default


class DocsAuthError(Exception):
    """Custom exception for Docs authentication errors"""
    pass


def create_session_token(docs_token: str) -> str:
    """Create a JWT session token for Docs access"""
    payload = {
        "docs_token": docs_token,
        "exp": datetime.utcnow() + timedelta(seconds=SESSION_DURATION),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SESSION_SECRET, algorithm="HS256")


def verify_session_token(token: str) -> Optional[Dict]:
    """Verify and decode a session token"""
    try:
        payload = jwt.decode(token, SESSION_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def get_current_docs_session(request: Request) -> Optional[Dict]:
    """Get current Docs session from cookie"""
    token = request.cookies.get("docs_session")
    if not token:
        return None
    return verify_session_token(token)


class DocsAPIClient:
    """Client for interacting with Docs API"""
    
    def __init__(self, api_token: str = None):
        # Use provided token or fall back to environment token
        self.api_token = api_token or DOCS_API_TOKEN
        
        if not self.api_token:
            raise DocsAuthError("No API token provided")
            
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def list_documents(self, limit: int = 100) -> List[Dict]:
        """List documents from Docs"""
        async with httpx.AsyncClient() as client:
            url = f"{DOCS_API_BASE_URL}/documents/"
            
            logger.info(f"Fetching documents from: {url}")
            
            response = await client.get(
                url,
                headers=self.headers,
                params={"limit": limit}
            )
            
            if response.status_code != 200:
                logger.error(f"API Response: {response.status_code} - {response.text}")
                raise DocsAuthError(f"Failed to list documents: {response.status_code}")
            
            data = response.json()
            # Handle paginated response
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            return data
    
    async def get_document(self, document_id: str) -> Dict:
        """Get document details"""
        async with httpx.AsyncClient() as client:
            url = f"{DOCS_API_BASE_URL}/documents/{document_id}/"
            
            response = await client.get(
                url,
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise DocsAuthError(f"Failed to get document: {response.status_code}")
            
            return response.json()
    
    async def create_document_for_owner(self, title: str, content: str) -> Dict:
        """Create a new document with markdown content"""
        async with httpx.AsyncClient() as client:
            url = f"{DOCS_API_BASE_URL}/documents/create-for-owner/"
            
            data = {
                "title": title,
                "content": content,  # Markdown content
                "format": "markdown"
            }
            
            response = await client.post(
                url,
                headers=self.headers,
                json=data
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create document: {response.status_code} - {response.text}")
                raise DocsAuthError(f"Failed to create document: {response.status_code}")
            
            return response.json()
    
    async def get_document_content_raw(self, document_id: str) -> str:
        """
        Get raw document content (base64 Yjs format)
        Note: This returns the raw Yjs content which needs special decoding
        """
        doc = await self.get_document(document_id)
        logger.info(f"Document structure: {doc}")
        # The content might be in a specific field depending on the API
        return doc.get("content", "") or doc.get("raw_content", "") or doc.get("body", "")
    
    async def search_documents(self, query: str) -> List[Dict]:
        """Search documents in Docs"""
        async with httpx.AsyncClient() as client:
            url = f"{DOCS_API_BASE_URL}/documents/"
            
            response = await client.get(
                url,
                headers=self.headers,
                params={"search": query}
            )
            
            if response.status_code != 200:
                raise DocsAuthError(f"Failed to search documents: {response.status_code}")
            
            data = response.json()
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            return data

    def extract_text_from_yjs(self, raw_content: str) -> str:
        """
        Attempt to extract readable text from Yjs base64 content
        This is a basic extraction that may not work for all cases
        """
        if not raw_content:
            return ""
        
        try:
            # Try to decode base64
            decoded = base64.b64decode(raw_content)
            
            # Try to extract text using simple heuristics
            # Yjs stores text in a binary format, we'll try to find readable strings
            text_parts = []
            current_text = ""
            
            for byte in decoded:
                if 32 <= byte <= 126:  # Printable ASCII
                    current_text += chr(byte)
                else:
                    if len(current_text) > 2:  # Only add strings longer than 2 chars
                        text_parts.append(current_text)
                    current_text = ""
            
            if len(current_text) > 2:
                text_parts.append(current_text)
            
            # Join with spaces and clean up
            extracted = " ".join(text_parts)
            
            # Remove common Yjs artifacts
            extracted = extracted.replace("paragraph", "").replace("text", "")
            extracted = " ".join(extracted.split())  # Normalize whitespace
            
            return extracted[:1000] if extracted else "[Contenu non lisible]"
            
        except Exception as e:
            logger.error(f"Failed to extract text from Yjs: {e}")
            return "[Erreur de décodage du contenu]"

    async def get_document_with_content(self, document_id: str) -> Dict:
        """Get document with extracted text content"""
        doc = await self.get_document(document_id)
        raw_content = self.get_document_content_raw_sync(doc)
        
        if raw_content:
            extracted_text = self.extract_text_from_yjs(raw_content)
            doc["extracted_content"] = extracted_text
        else:
            doc["extracted_content"] = "[Aucun contenu disponible]"
            
        return doc

    def get_document_content_raw_sync(self, doc: Dict) -> str:
        """Get raw content from document dict (synchronous)"""
        return doc.get("content", "") or doc.get("raw_content", "") or doc.get("body", "")