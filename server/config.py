import os
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Union
from enum import Enum
import json


HOSTNAME = os.environ['HOSTNAME']

class PluginConfig(BaseModel): 
    """
    The user-customizable part of PluginConfig
    """
    name_for_model:         Optional[str] 
    name_for_human:         Optional[str] 
    description_for_model:	Optional[str] 
    description_for_human:	Optional[str] 
    logo:                   Optional[str] 


class PluginAuthConfig(BaseModel):
    """ one of a few types of auth configurations"""

class PluginAuthConfigBearer(PluginAuthConfig):
    type: str = "user_http"
    authorization_type: str = "bearer"

class PluginAuthConfigNone(PluginAuthConfig):
    type: str = "none"


class PluginApiConfig(BaseModel):
    type: str = "openapi"
    url: HttpUrl = f"https://{HOSTNAME}.gpt-gateway.com/.well-known/openapi.yaml"
    has_user_authentication: bool = False

class FullPluginConfig(BaseModel):
    schema_version:        str = "v1"
    name_for_model:        str = "retrieval"
    name_for_human:        str = "Retrieval Plugin"
    description_for_model: str = "Plugin for searching through the user's documents (such as files, emails, and more) to find answers to questions and retrieve relevant information. Use it whenever a user asks something that might be found in their personal information."
    description_for_human: str = "Search through your documents."
    auth:     PluginAuthConfig = PluginAuthConfigNone()
    api:       PluginApiConfig = PluginApiConfig()
    logo_url:          HttpUrl = f"https://{HOSTNAME}.gpt-gateway.com/.well-known/logo.png"
    contact_email:         str = "hello@gpt-gateway.com"
    legal_info_url:    HttpUrl = "https://gpt-gateway/legal"



class EmbeddingConfig(BaseModel):
    model     : Optional[str] 

    
class ChatConfig(BaseModel):
    system_prompt: Optional[str] 
    
class AuthConfig(BaseModel):
    """
    a list of valid api keys provisioned into a runtime
    """
    bearer_token_a:  str 
    bearer_token_b:  str 


class ChunkConfig(BaseModel):
    chunk_size:                 int = 200     # The target size of each text chunk in tokens
    min_chunk_size_chars:       int = 350     # The minimum size of each text chunk in characters
    min_chunk_length_to_embed:  int = 5       # Discard chunks shorter than this
    embeddings_batch_size:      int = 128     # The number of embeddings to request at a time
    max_num_chunks:             int = 10000   # The maximum number of chunks to generate from a text


class ServiceConfig(BaseModel):
    """
    The configuration for a service that is pased to the runtime as json via an environment variable
    """
    plugin:    Optional[PluginConfig]
    embedding: Optional[EmbeddingConfig]
    chat:      Optional[ChatConfig]
    auth:      Optional[AuthConfig]
    chunk:     Optional[ChunkConfig]       = ChunkConfig()


class ExtractMetadataConfig(BaseModel):
    extract: bool = False
    
service_config = os.environ.get('SERVICE_CONFIG')
    
service_config = ServiceConfig(**json.loads(service_config))

chunk_config = service_config.chunk


extract_metadata_config = ExtractMetadataConfig()