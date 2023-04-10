from loguru import logger
from fastapi import HTTPException
from server.config import HOSTNAME, sub_access, oauth_config
from fastapi import Request
from fastapi.responses import RedirectResponse
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import httpx
from pydantic import BaseModel
from server.main import app
from server.auth import verified_sub
from server.config import auth_tokens
import os
import base64
import json

GPTG_OAUTH_CLIENT_ID     = os.environ['GPTG_AUTH_CHATGPT_CLIENT_ID']
GPTG_OAUTH_CLIENT_SECRET = os.environ['GPTG_AUTH_CHATGPT_CLIENT_SECRET']
AUTH_HOSTNAME            = 'auth.gpt-gateway.com'
GPTG_OAUTH_AUTHORIZE_URL = f"https://{AUTH_HOSTNAME}/oauth/token"
GTPG_REDIRECT_URL        = f"https://{HOSTNAME}.gpt-gateway.com/oauth/callback"

original_redirect_uri = ""

@app.get('/authorize', include_in_schema=False)
async def authorize(request: Request):
    original_url = str(request.url)
    new_url = replace_redirect_uri(original_url)
    return RedirectResponse(new_url)


def replace_redirect_uri(original_url: str) -> str:
    global original_redirect_uri
    
    # Parse the original URL
    parsed_url = urlparse(original_url)

    # Parse the query parameters
    query_params = parse_qs(parsed_url.query)

    if 'redirect_uri' not in query_params:
        logger.warning("No redirect_uri in query_params")
        raise HTTPException(status_code=400, detail="No redirect_uri in query_params")
    if 'client_id' not in query_params:
        logger.warning("No client_id in query_params")
        raise HTTPException(status_code=400, detail="No client_id in query_params")

    # validate the client_id
    if oauth_config.client_id != query_params['client_id'][0]:
        logger.warning(f"Invalid client_id {query_params['client_id'][0]}")
        raise HTTPException(status_code=400, detail="Invalid client_id")

    # replace the client id with our own backend auth client id
    query_params['client_id'] = [GPTG_OAUTH_CLIENT_ID]
    
    # save the original redirect_uri (todo: validate it is from our expected set of valid redirect_uris)
    original_redirect_uri = query_params['redirect_uri'][0]
    
    if not original_redirect_uri.startswith('https://chat.openai.com/aip/'):
        logger.warning(f"Invalid redirect_uri {original_redirect_uri}")
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    
    # Replace the 'redirect_uri' value to point to our own callback endpoint
    query_params['redirect_uri'] = [GTPG_REDIRECT_URL]

    # Reconstruct the query string with the updated parameters
    new_query = urlencode(query_params, doseq=True)
    # Reconstruct the URL with the updated query string and new hostname. Replace "scheme" to "https" and "host" to "new_hostname"
    new_url = urlunparse(parsed_url._replace(scheme="https", netloc=AUTH_HOSTNAME, path="/authorize", query=new_query))
    return new_url


@app.get('/oauth/callback', include_in_schema=False)
async def callback(request: Request):
    original_url = str(request.url)
    query = original_url.split("?")[1]
    new_url = f"{original_redirect_uri}?{query}"
    return RedirectResponse(new_url)




class TokenRequest(BaseModel):
    grant_type:    str
    client_id:     str
    client_secret: str
    code:          str
    redirect_uri:  str

@app.post('/oauth/token', include_in_schema=False)
async def token(request:       Request, 
                token_request: TokenRequest):
    
    if token_request.redirect_uri != original_redirect_uri:
        logger.warning(f"redirect_uri doesn't match: {token_request.redirect_uri} != {original_redirect_uri}")
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")

    if token_request.client_id != oauth_config.client_id:
        logger.warning(f"client_id doesn't match: {token_request.client_id} != {GPTG_OAUTH_CLIENT_ID}")
        raise HTTPException(status_code=400, detail="client_id mismatch")
    
    if token_request.client_secret != oauth_config.client_secret:
        logger.warning(f"client_secret doesn't match: {token_request.client_secret} != {GPTG_OAUTH_CLIENT_SECRET}")
        raise HTTPException(status_code=400, detail="client_secret mismatch")

    # replace the client id/secret with our own backend auth client id/secret
    token_request.client_id     = GPTG_OAUTH_CLIENT_ID
    token_request.client_secret = GPTG_OAUTH_CLIENT_SECRET
    token_request.redirect_uri  = GTPG_REDIRECT_URL
    
    async with httpx.AsyncClient() as client:
        response = await client.post(GPTG_OAUTH_AUTHORIZE_URL, json=token_request.dict())
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    response_json = response.json()
    # get sub from access_token and confirm sub has access to this plugin
    # will transition to audience claim in the future
    sub = json.loads(base64.b64decode(response_json['access_token'].split(".")[1])).get('sub')
    if sub not in sub_access.read:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return response_json


