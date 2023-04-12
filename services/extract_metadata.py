from loguru import logger
from models.models import Source
from services.openai import get_chat_completion
import json
from typing import Dict
from server.config import extract_metadata_config

def extract_metadata_from_document(text: str) -> Dict[str, str]:

    config = json.loads(extract_metadata_config.json())
    model = config.pop("model")    
    allowed_keys = {k for k, v in config.items() if v}
    if not allowed_keys:
        logger.info("No metadata extraction is enabled")
        return {}  # no extraction is enabled
    
    sources = Source.__members__.keys()
    sources_string = ", ".join(sources)
    messages = [
        {
            "role": "system",
            "content": f"""
            Given the beginning of some content from a user, please extract the following metadata:
            - title: string (or None if unknown) of the title of the content.  If no title is specified output a good short title for the content.            
            - author: string (or None if unknown) of the author of the content.
            - created_at: string (or None if unknown) of the data in the format YYYY-MM-DD that the content was created if it appears in the content.            
            Please respond with JSON output containing the extracted metadata in key value pairs. 
            The keys for the metadata are "created_at", "author", and "title".
            If you don't find a metadata field, you don't need to include it.  Do not use "unknown", "not found" or similar as output values.
            """,
        },
        {"role": "user", "content": text[:2048]},
    ]

    completion = get_chat_completion(messages, model=model)


    try:
        metadata = json.loads(completion)
        metadata = {key: value for key, value in metadata.items() if key in allowed_keys}
        for k, v in metadata.items():
            logger.info(f"Extracted metadata {k}={v}")
        metadata = {k: v for k, v in metadata.items() if v}   # remove empty/None values
    except:
        metadata = {}

    return metadata
