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

class OpenAIPluginAuthConfigOAuth(BaseModel):
    """
    The Plugin Oauth configuration as it is presented in the ai-plugin.json 
    """
    type:                       str         = Field("oauth", const=True)
    client_url:                 HttpUrl     = Field(description="ChatGPT will direct the user’s browser to this url to log in to the plugin")
    authorization_url:          HttpUrl     = Field(description="After successful login ChatGPT will complete the OAuth flow by making a POST request to this URL")
    scope:                      str         = Field(description="The scope used for the OAuth flow")    
    authorization_content_type: str         = Field("application/json", const=True)
    verification_tokens:        OpenAIVerificationToken = Field(description="The verification token to send to OpenAI for the plugin")


class PluginAuthConfigOAuth(BaseModel):
    """
    The Plugin Oauth configuration as managed by GPT-Gateway
    """    
    client_url:                 HttpUrl     = Field(description="ChatGPT will direct the user’s browser to this url to log in to the plugin")
    authorization_url:          HttpUrl     = Field(description="After successful login ChatGPT will complete the OAuth flow by making a POST request to this URL")
    scope:                      str         = Field(description="The scope used for the OAuth flow")
    client_id:                  str         = Field(unique=True, index=True, description="The client id to send to OpenAI for the plugin")
    client_secret:              str         = Field(description="The client secret to send to OpenAI for the plugin")
    openai_verification_token:  str         = Field(description="The verification token specified by OpenAI to configure in the plugin")
    


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


class AccessPermission(BaseModel):
    write: List[str]         # list of token subscribers that can write & read the collection
    read:  List[str]         # list of token subscribers that can read from the collection



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
    access:       AccessPermission

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
    logo_url:              HttpUrl = f"https://{HOSTNAME}.gpt-gateway.com/.well-known/logo.png"
    contact_email:         str     = "hello@gpt-gateway.com"
    legal_info_url:        HttpUrl = "https://gpt-gateway.com/legal"


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

ouath_config = service_config.oauth_config

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
                                 auth=auth, 
                                 api=api)

logger.info(plugin_config)