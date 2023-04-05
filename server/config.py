from loguru import logger
import os
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Union
from enum import Enum
import json

HOSTNAME = os.environ['HOSTNAME']   

# User Configurable items 

class PluginAuthType(Enum):
    bearer = "bearer"
    none   = "none"
    oauth  = "oauth"
    
class OpenAIVerificationToken(BaseModel):
    openai: str

class PluginAuthConfigOAuth(BaseModel):
    """
    Plugin auth config for plugin auth_type "oauth"
    """
    type:                       str         = Field("oauth", const=True)
    client_url:                 HttpUrl     = "" #f"https://{HOSTNAME}.gpt-gateway.com/authorize"
    scope:                      str         = ""
    authorization_url:          HttpUrl     = "" #f"https://{HOSTNAME}.gpt-gateway.com/token"
    authorization_content_type: str         = "application/json"
    verification_tokens:        OpenAIVerificationToken



class PluginConfig(BaseModel): 
    """
    The user-customizable part of PluginConfig
    """
    name_for_model:        str = "retrieval"
    name_for_human:        str = f"{HOSTNAME} Plugin"
    description_for_model: str = f"Plugin for searching through the user's collection of '{HOSTNAME}' documents (such as files, emails, and more) to find answers to questions and retrieve relevant information. Use it whenever a user asks something that might be found in their personal information."
    description_for_human: str = f"Search through your collection of '{HOSTNAME}' documents."    
    logo:                  Optional[str] 
    auth_type:             PluginAuthType  = PluginAuthType.none     
    


class EmbeddingConfig(BaseModel):
    model : str   = "text-embedding-ada-002"
    
    
class ServiceBearerTokenConfig(BaseModel):
    """
    A list bearer tokens that are authorized to access the primary / api.
    This authorization is separate from the authorization for the /plugin api.
    """
    authorized_tokens : List[str]  =  []

    
class ChunkConfig(BaseModel):
    """
    configuration for chunking policy
    """
    chunk_size:                 int = 200     # The target size of each text chunk in tokens
    min_chunk_size_chars:       int = 350     # The minimum size of each text chunk in characters
    min_chunk_length_to_embed:  int = 5       # Discard chunks shorter than this
    embeddings_batch_size:      int = 128     # The number of embeddings to request at a time
    max_num_chunks:             int = 10000   # The maximum number of chunks to generate from a text



class ExtractMetadataConfig(BaseModel):
    """
    configuration for metadata extraction
    """
    created_at:  bool    = False
    author:      bool    = False
    title:       bool    = False
    model:       str     = "gpt-4"


class ServiceConfig(BaseModel):
    """
    The configuration for a service that is passed to the runtime as json via an environment variable
    """
    plugin:       PluginConfig             = PluginConfig()
    embedding:    EmbeddingConfig          = EmbeddingConfig()
    plugin_auth:  PluginAuthType           = PluginAuthType.bearer    
    auth_tokens:  ServiceBearerTokenConfig = ServiceBearerTokenConfig()
    chunk:        ChunkConfig              = ChunkConfig()
    extract:      ExtractMetadataConfig    = ExtractMetadataConfig()
    oauth_config: Optional[PluginAuthConfigOAuth]

 ##
 ## End user-configurable items
 ##


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
    url: HttpUrl = f"https://{HOSTNAME}.gpt-gateway.com/.well-known/openapi.yaml"
    has_user_authentication: bool = False

    
class FullPluginConfigV1(BaseModel):
    """
    Full plugin configuration, only partially exposed to the user
    Used to generate .well-known/ai-plugin.json
    """
    schema_version:        str = Field("v1", const=True)
    name_for_model:        str 
    name_for_human:        str 
    description_for_model: str 
    description_for_human: str 
    auth:                  Union[PluginAuthConfigBearer, PluginAuthConfigNone, PluginAuthConfigOAuth]                                 
    api:                   PluginApiConfig 
    logo_url:              HttpUrl = f"https://{HOSTNAME}.gpt-gateway.com/.well-known/logo.png"
    contact_email:         str     = "hello@gpt-gateway.com"
    legal_info_url:        HttpUrl = "https://gpt-gateway/legal"


##  Load Config from Environment
service_config = os.environ.get('SERVICE_CONFIG')
    
service_config = ServiceConfig(**json.loads(service_config))

#  convenience variables
chunk_config = service_config.chunk
logger.info(chunk_config)

extract_metadata_config = service_config.extract
logger.info(extract_metadata_config)

auth_tokens = service_config.auth_tokens

embedding_config = service_config.embedding
logger.info(embedding_config)

# assemble plugin config 

user_plugin_config = service_config.plugin

service_config.plugin_auth = PluginAuthType.none  # force to none for now

if service_config.plugin_auth == PluginAuthType.bearer:
    auth = PluginAuthConfigBearer()
    has_user_authentication = True
elif service_config.plugin_auth == PluginAuthType.oauth:
    auth = PluginAuthConfigOAuth(**service_config.oauth_config.dict())
    has_user_authentication = True
elif service_config.plugin_auth == PluginAuthType.none:
    auth = PluginAuthConfigNone()
    has_user_authentication = False
else:
    logger.error(f"Unknown auth_type: {user_plugin_config.auth_type}")
    raise ValueError(f"Unknown auth_type: {user_plugin_config.auth_type}")

api = PluginApiConfig(has_user_authentication=has_user_authentication)

plugin_config = FullPluginConfigV1(name_for_model = user_plugin_config.name_for_model,
                                   name_for_human = user_plugin_config.name_for_human,
                                   description_for_model = user_plugin_config.description_for_model,
                                   description_for_human = user_plugin_config.description_for_human,
                                   auth=auth, 
                                   api=api)

logger.info(plugin_config)