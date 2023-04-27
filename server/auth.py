from loguru import logger
from fastapi import HTTPException
import jwt
import os

DOMAIN = "auth.jiggy.ai"
API_AUDIENCE = "https://api.gpt-gateway.com"
ALGORITHMS = ["RS256"]
ISSUER = "https://"+DOMAIN+"/"

jwks_url = 'https://%s/.well-known/jwks.json' % DOMAIN
jwks_client = jwt.PyJWKClient(jwks_url)


JWT_RSA_PUBLIC_KEY = os.environ['JIGGY_JWT_RSA_PUBLIC_KEY']
JIGGY_JWT_ISSUER = "Jiggy.AI"



def verify_jiggy_api_token(credentials):
    """Perform Jiggy API token verification using PyJWT.  raise HTTPException on error"""
    try:
        payload = jwt.decode(credentials,
                             JWT_RSA_PUBLIC_KEY,
                             algorithms=ALGORITHMS,
                             issuer=JIGGY_JWT_ISSUER)
    except Exception as e:
        logger.warning(f'Error decoding token: {e}')        
        raise HTTPException(status_code=401, detail=f"Invalid api auth token ({e})")
    return payload


def verify_auth0_token(credentials):
    """Perform auth0 token verification using PyJWT.  raise HTTPException on error"""
    # This gets the 'kid' from the passed token
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(credentials).key
    except Exception as error:
        logger.error(f'Error getting signing key: {error}')
        raise HTTPException(status_code=401, detail=f"Unknown auth token ({error})")    
    try:        
        payload = jwt.decode(credentials,
                             signing_key,
                             algorithms=ALGORITHMS,
                             audience=API_AUDIENCE,
                             issuer=ISSUER)        
    except Exception as e:
        logger.warning(f'Error decoding token: {e}')
        raise HTTPException(status_code=401, detail=f"Invalid auth token ({e})")
    return payload



def verified_sub(token):
    """
    verify the supplied token and return the associated subject id (sub)
    """
    # determine if this is a jiggy api key token or an auth0 token
    try:
        iss = jwt.decode(token.credentials, options={"verify_signature": False}).get('iss')
    except:
        logger.error("unable to decode token to determine iss")
        raise HTTPException(status_code=401, detail=f"Invalid auth token")
    
    if iss == JIGGY_JWT_ISSUER:
        return verify_jiggy_api_token(token.credentials)['sub']
    else:
        return verify_auth0_token(token.credentials)['sub']

