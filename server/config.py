from loguru import logger
import os
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Union
from enum import Enum
import json

from jiggybase.models import (
    PluginAuthType,
    OpenAIVerificationToken,
    OpenAIPluginAuthConfigOAuth,
    PluginAuthConfigOAuth,
    PluginConfig,
    EmbeddingConfig,
    PluginBearerTokenConfig,
    ChunkConfig,
    ExtractMetadataConfig,    
    )


HOSTNAME = os.environ['HOSTNAME']   



class AccessPermission(BaseModel):
    write: List[str]         # list of token subscribers that can write & read the collection
    read:  List[str]         # list of token subscribers that can read from the collection



class ServiceConfig(BaseModel):
    """
    The configuration for a service that is passed to the runtime as json via an environment variable
    """
    plugin:       PluginConfig             
    embedding:    EmbeddingConfig          
    plugin_auth:  PluginAuthType           
    auth_tokens:  PluginBearerTokenConfig 
    chunk:        ChunkConfig             
    extract:      ExtractMetadataConfig   
    oauth_config: Optional[PluginAuthConfigOAuth]
    access:       AccessPermission


class PluginAuthConfigBearer(BaseModel):
    """
    Static bearer token auth for the /plugin api
    ServiceBearerTokenConfig is used to configure the list of authorized tokens
    """
    type:               str = Field("user_http", const=True)
    authorization_type: str = Field("bearer", const=True)

class PluginAuthConfigNone(BaseModel):
    """
    No authentication, anyone can access the /plugin api without auth
    """
    type: str = Field("none", const=True)
    

class PluginApiConfig(BaseModel):
    type: str = "openapi"
    url: HttpUrl = f"https://{HOSTNAME}.plugin.jiggy.ai/.well-known/openapi.yaml"
    has_user_authentication: bool = False

    
class AIPluginConfigV1(BaseModel):
    """
    Full plugin configuration 
    used to generate .well-known/ai-plugin.json
    """
    schema_version:        str = Field("v1", const=True)
    name_for_model:        str 
    name_for_human:        str 
    description_for_model: str 
    description_for_human: str 
    auth:                  Union[PluginAuthConfigBearer, PluginAuthConfigNone, OpenAIPluginAuthConfigOAuth] 
    api:                   PluginApiConfig 
    logo_url:              HttpUrl = f"https://{HOSTNAME}.plugin.jiggy.ai/.well-known/logo.png"
    contact_email:         str     = "jiggybase@jiggy.ai"
    legal_info_url:        HttpUrl = "https://jiggy.ai/legal"


##  Load Config from Environment
service_config = os.environ.get('SERVICE_CONFIG')
    
service_config = ServiceConfig(**json.loads(service_config))

# break out into convenience variables for other modules
chunk_config = service_config.chunk
logger.info(chunk_config)

extract_metadata_config = service_config.extract
logger.info(extract_metadata_config)

auth_tokens = service_config.auth_tokens

embedding_config = service_config.embedding
logger.info(embedding_config)

plugin_auth = service_config.plugin_auth
logger.info(plugin_auth)

oauth_config = service_config.oauth_config

# subscriber access -- list of auth0 subscriber IDs
sub_access = service_config.access
sub_access.read = sub_access.read + sub_access.write   # read access includes write access
logger.info(f"sub_access: {sub_access}")


# assemble ai-plugin.json config 

user_plugin_config = service_config.plugin   # the user-configurable part of the plugin config

if service_config.plugin_auth == PluginAuthType.bearer:
    auth = PluginAuthConfigBearer()
    has_user_authentication = True
elif service_config.plugin_auth == PluginAuthType.oauth:
    vtoken = OpenAIVerificationToken(openai=service_config.oauth_config.openai_verification_token)
    auth = OpenAIPluginAuthConfigOAuth(**service_config.oauth_config.dict(), verification_tokens=vtoken)
    logger.info(auth)
    has_user_authentication = True
elif service_config.plugin_auth == PluginAuthType.none:
    auth = PluginAuthConfigNone()
    has_user_authentication = False
else:
    logger.error(f"Unknown auth_type: {user_plugin_config.auth_type}")
    raise ValueError(f"Unknown auth_type: {user_plugin_config.auth_type}")

 
api = PluginApiConfig(has_user_authentication=has_user_authentication)

plugin_config = AIPluginConfigV1(name_for_model = user_plugin_config.name_for_model,
                                 name_for_human = user_plugin_config.name_for_human,
                                 description_for_model = user_plugin_config.description_for_model,
                                 description_for_human = user_plugin_config.description_for_human,
                                 logo_url = user_plugin_config.logo_url if user_plugin_config.logo_url else f"https://{HOSTNAME}.plugin.jiggy.ai/.well-known/logo.png",
                                 auth=auth, 
                                 api=api)

logger.info(plugin_config)
