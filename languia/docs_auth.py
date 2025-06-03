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
    """
    Client for interacting with the Docs API.
    
    Provides methods to fetch documents and extract content from Docs,
    with proper error handling and timeout management.
    """
    
    def __init__(self, api_token: str = None):
        """
        Initialize the Docs API client.
        
        Args:
            api_token (str, optional): API token for authentication.
                                     Falls back to DOCS_API_TOKEN environment variable.
                                     
        Raises:
            DocsAuthError: If no API token is provided.
        """
        self.api_token = api_token or DOCS_API_TOKEN
        
        if not self.api_token:
            raise DocsAuthError("No API token provided")
            
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def list_documents(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve a list of documents from the Docs API.
        
        Args:
            limit (int): Maximum number of documents to retrieve (default: 100)
            
        Returns:
            List[Dict]: List of document objects with metadata
            
        Raises:
            DocsAuthError: If API request fails or times out
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
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
        except httpx.TimeoutException:
            logger.error("Timeout while fetching documents from Docs API")
            raise DocsAuthError("Timeout while fetching documents")
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching documents: {e}")
            raise DocsAuthError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching documents: {e}")
            raise DocsAuthError(f"Unexpected error: {e}")
    
    async def get_document(self, document_id: str) -> Dict:
        """
        Retrieve detailed information for a specific document.
        
        Args:
            document_id (str): Unique identifier for the document
            
        Returns:
            Dict: Document object with content and metadata
            
        Raises:
            DocsAuthError: If API request fails or document not found
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                url = f"{DOCS_API_BASE_URL}/documents/{document_id}/"
                
                response = await client.get(
                    url,
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get document {document_id}: {response.status_code} - {response.text}")
                    raise DocsAuthError(f"Failed to get document: {response.status_code}")
                
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching document {document_id}")
            raise DocsAuthError("Timeout while fetching document")
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching document {document_id}: {e}")
            raise DocsAuthError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching document {document_id}: {e}")
            raise DocsAuthError(f"Unexpected error: {e}")
    
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
        Extract readable text from Yjs base64 content using pycrdt with regex fallback
        """
        if not raw_content:
            return ""
        
        # First, try to use pycrdt for proper YJS parsing
        try:
            from pycrdt import Doc, Text, Map, Array
            
            # Decode base64 to binary
            decoded = base64.b64decode(raw_content)
            
            # Create a new document and apply the update
            doc = Doc()
            
            # Wrap in try-except as apply_update can panic on invalid data
            try:
                doc.apply_update(decoded)
            except:
                # Not valid YJS data, fall back to regex
                raise ValueError("Not a valid YJS document")
            
            # Function to recursively extract text from YJS structures
            def extract_text_from_item(item):
                """Recursively extract text from different YJS types"""
                texts = []
                
                if isinstance(item, Text):
                    text_content = item.to_py()
                    if text_content and len(text_content.strip()) > 10:
                        texts.append(text_content)
                
                elif isinstance(item, Array):
                    for element in item.to_py():
                        if isinstance(element, str) and len(element.strip()) > 10:
                            texts.append(element)
                        elif isinstance(element, (dict, list)):
                            # Recursively process nested structures
                            texts.extend(extract_text_from_nested(element))
                
                elif isinstance(item, Map):
                    map_data = item.to_py()
                    for key, value in map_data.items():
                        if isinstance(value, str) and len(value.strip()) > 10:
                            texts.append(value)
                        elif isinstance(value, (dict, list)):
                            texts.extend(extract_text_from_nested(value))
                
                return texts
            
            def extract_text_from_nested(data):
                """Extract text from nested Python structures"""
                texts = []
                
                if isinstance(data, dict):
                    for value in data.values():
                        if isinstance(value, str) and len(value.strip()) > 10:
                            texts.append(value)
                        elif isinstance(value, (dict, list)):
                            texts.extend(extract_text_from_nested(value))
                
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, str) and len(item.strip()) > 10:
                            texts.append(item)
                        elif isinstance(item, (dict, list)):
                            texts.extend(extract_text_from_nested(item))
                
                return texts
            
            # Extract all text content
            all_texts = []
            
            # Try different approaches to access the document content
            # Approach 1: Try common field names with different types
            common_fields = ['content', 'text', 'body', 'data', 'document', 'value', 
                           'title', 'description', 'sections', 'metadata']
            
            for field_name in common_fields:
                # Try as Text
                try:
                    text_obj = doc.get(field_name, type=Text)
                    if text_obj:
                        text_content = str(text_obj)
                        if text_content and len(text_content.strip()) > 10:
                            all_texts.append(text_content)
                except:
                    pass
                
                # Try as Array
                try:
                    array_obj = doc.get(field_name, type=Array)
                    if array_obj:
                        all_texts.extend(extract_text_from_item(array_obj))
                except:
                    pass
                
                # Try as Map
                try:
                    map_obj = doc.get(field_name, type=Map)
                    if map_obj:
                        all_texts.extend(extract_text_from_item(map_obj))
                except:
                    pass
            
            # Approach 2: Try to get the root map and iterate
            try:
                # Some YJS documents store everything in a root map
                root_map = doc.get("", type=Map)
                if root_map:
                    for key in root_map:
                        try:
                            value = root_map[key]
                            if isinstance(value, str) and len(value.strip()) > 10:
                                all_texts.append(value)
                            elif hasattr(value, 'to_py'):
                                py_value = value.to_py()
                                all_texts.extend(extract_text_from_nested(py_value))
                        except:
                            pass
            except:
                pass
            
            # Remove duplicates while preserving order
            seen = set()
            unique_texts = []
            for text in all_texts:
                if text not in seen:
                    seen.add(text)
                    unique_texts.append(text)
            
            # If we found content, join and return it
            if unique_texts:
                result = "\n\n".join(unique_texts)
                # Clean up the result
                import re
                result = re.sub(r'\n{3,}', '\n\n', result).strip()
                
                # Remove technical artifacts
                lines = result.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Skip lines that look like technical metadata
                    if not any(pattern in line.lower() for pattern in [
                        'blockid', 'blockgroup', 'w3broadcast', 'initialblock',
                        'backgroundcolor', 'alignment', 'fontfamily'
                    ]):
                        cleaned_lines.append(line)
                
                result = '\n'.join(cleaned_lines)
                
                if len(result) > 50:  # Only return if we found substantial content
                    return result
        
        except ImportError:
            logger.warning("pycrdt not installed, falling back to regex extraction")
        except Exception as e:
            # pycrdt can throw various exceptions including PanicException
            logger.debug(f"pycrdt parsing failed: {type(e).__name__}: {e}, falling back to regex extraction")
        
        # Fallback to regex-based extraction
        try:
            import re
            
            # Decode base64 (already done if pycrdt was tried)
            if 'decoded' not in locals():
                decoded = base64.b64decode(raw_content)
            
            # Convert to string and handle UTF-8
            try:
                content_str = decoded.decode('utf-8', errors='ignore')
            except:
                content_str = decoded.decode('latin-1', errors='ignore')
            
            # Look for meaningful text patterns - complete sentences and paragraphs
            # Use regex to find text blocks that look like real content
            
            # Find text that looks like sentences (contains letters, spaces, punctuation)
            sentence_pattern = r'[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\',\.\?\!\:\;]{20,200}[\.!\?]'
            sentences = re.findall(sentence_pattern, content_str)
            
            # Also look for longer text blocks that might be paragraphs
            paragraph_pattern = r'[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\',\.\?\!\:\;\(\)]{50,500}'
            paragraphs = re.findall(paragraph_pattern, content_str)
            
            # Combine all found text
            all_text_blocks = sentences + paragraphs
            
            if not all_text_blocks:
                # Fallback: extract any text that looks meaningful
                word_pattern = r'[A-Za-zÀ-ÿ]{3,}(?:\s+[A-Za-zÀ-ÿ]{2,}){2,}'
                words_blocks = re.findall(word_pattern, content_str)
                all_text_blocks = words_blocks
            
            if not all_text_blocks:
                return "[Contenu non lisible]"
            
            # Filter and clean the text blocks
            cleaned_blocks = []
            
            for block in all_text_blocks:
                # Skip blocks with too many technical patterns
                if any(pattern in block.lower() for pattern in [
                    'doc-', 'blockgroup', 'blockcontainer', 'href', 'target', 'class',
                    'bullet', 'hardbreak', 'paragraph', 'heading', 'w3broadcast',
                    'initialblockid', 'backgroundcolor', 'alignment', 'default('
                ]):
                    continue
                
                # Skip blocks that are mostly non-alphabetic
                alpha_count = sum(1 for c in block if c.isalpha())
                if alpha_count < len(block) * 0.5:  # At least 50% letters
                    continue
                
                # Skip very short blocks
                if len(block.strip()) < 20:
                    continue
                
                # Clean the block
                cleaned = block.strip()
                
                # Fix common encoding issues in French
                encoding_fixes = {
                    ' à ': ' à ',
                    ' è ': ' è ',
                    ' é ': ' é ',
                    ' ê ': ' ê ',
                    ' ç ': ' ç ',
                    ' ù ': ' ù ',
                    ' û ': ' û ',
                    ' ô ': ' ô ',
                    ' î ': ' î ',
                    ' modèles ': ' modèles ',
                    ' problème ': ' problème ',
                    ' résultats ': ' résultats ',
                    ' créé ': ' créé ',
                    ' données ': ' données ',
                    ' entraînés ': ' entraînés ',
                    ' génèrent ': ' génèrent ',
                    ' stéréotypés ': ' stéréotypés ',
                    'd\'IA': 'd\'IA',
                    ' sûrs ': ' sûrs '
                }
                
                for wrong, correct in encoding_fixes.items():
                    cleaned = cleaned.replace(wrong, correct)
                
                cleaned_blocks.append(cleaned)
            
            if not cleaned_blocks:
                return "[Contenu non lisible]"
            
            # Sort by length (longer blocks are likely more meaningful content)
            cleaned_blocks.sort(key=len, reverse=True)
            
            # Take all cleaned blocks (no limit)
            result = " ".join(cleaned_blocks)
            
            # Final cleanup
            result = re.sub(r'\s+', ' ', result).strip()
            
            return result if result else "[Contenu non lisible]"
                
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