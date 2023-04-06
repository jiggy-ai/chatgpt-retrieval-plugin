from loguru import logger
from fastapi import HTTPException
import jwt
import os

DOMAIN = "auth.gpt-gateway.com"
API_AUDIENCE = "https://api.gpt-gateway.com"
ALGORITHMS = ["RS256"]
ISSUER = "https://"+DOMAIN+"/"

jwks_url = 'https://%s/.well-known/jwks.json' % DOMAIN
jwks_client = jwt.PyJWKClient(jwks_url)


JWT_RSA_PUBLIC_KEY = os.environ['JIGGY_JWT_RSA_PUBLIC_KEY']
JWT_ISSUER = "Jiggy.AI"



def verify_jiggy_api_token(credentials):
    """Perform Jiggy API token verification using PyJWT.  raise HTTPException on error"""
    # This gets the 'kid' from the passed token credentials
    signing_key = JWT_RSA_PUBLIC_KEY    
    try:
        payload = jwt.decode(credentials,
                             signing_key,
                             algorithms=ALGORITHMS,
                             issuer=JWT_ISSUER)
    except Exception as e:
        logger.warning(f'Error decoding token: {e}')        
        raise HTTPException(status_code=401, detail=str(e))
    return payload



def verify_auth0_token(credentials):
    """Perform auth0 token verification using PyJWT.  raise HTTPException on error"""
    # This gets the 'kid' from the passed token
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(credentials).key
    except jwt.exceptions.PyJWKClientError as error:
        logger.warning(f'Error getting signing key: {error}')
        raise HTTPException(status_code=401, detail=str(error))
    except jwt.exceptions.DecodeError as error:
        logger.warning(f'Error decoding token: {error}')      
        raise HTTPException(status_code=401, detail=str(error))
    except Exception as error:
        logger.warning(f'Error verifying token: {error}')
        raise HTTPException(status_code=401, detail=str(error))
    
    try:
        payload = jwt.decode(credentials,
                             signing_key,
                             algorithms=ALGORITHMS,
                             audience=API_AUDIENCE,
                             issuer=ISSUER)
    except Exception as e:
        logger.warning(f'Error decoding token: {e}')
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return payload



def verified_sub(token):
    """
    verify the supplied token and return the associated sub
    """
    try:
        return verify_jiggy_api_token(token.credentials)['sub']
    except:            
        return verify_auth0_token(token.credentials)['sub']

