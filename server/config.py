import os
from pydantic import BaseModel
from typing import List, Optional, Union
from enum import Enum
import json
import base64

class PluginConfig(BaseModel): 
    name_for_model:         Optional[str] 
    name_for_human:         Optional[str] 
    description_for_model:	Optional[str] 
    description_for_human:	Optional[str] 
    logo:                   Optional[str] 

class EmbeddingConfig(BaseModel):
    model     : Optional[str] 
    chunksize : Optional[int] 
    include_headers : Optional[bool] 
    
class ChatConfig(BaseModel):
    system_prompt: Optional[str] 
    
class AuthConfig(BaseModel):
    """
    a list of valid api keys provisioned into a runtime
    """
    bearer_token_a:  str 
    bearer_token_b:  str 


class ServiceConfig(BaseModel):
    """
    The configuration for a service that is pased to the runtime as json via an environment variable
    """
    plugin: Optional[PluginConfig]
    embedding: Optional[EmbeddingConfig]
    chat: Optional[ChatConfig]
    auth: Optional[AuthConfig]
        

service_config = os.environ.get['SERVICE_CONFIG']
    
service_config = ServiceConfig(**json.loads(service_config))

