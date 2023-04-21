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

    # add language to allowed keys
    allowed_keys.add("language")
    
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
            - language: string, the 2 character ISO 639-1 language code of the primary language of the content.
            Please respond with JSON output containing the extracted metadata in key value pairs. 
            The keys for the metadata are "title", "author", "created_at", and "language".
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



def csv_header(text: str) -> list[str]:
    model = 'gpt-3.5-turbo'
    messages = [
        {
            "role": "system",
            "content": "Please output a json list of header names for the following csv data.",
        },
        {"role": "user", "content": text},
    ]
    completion = get_chat_completion(messages, model=model)
    try:
        headers = json.loads(completion)      
    except:
        headers = []
    logger.info(f"Extracted headers: {headers}")
    return headers



def csv_has_header(rows) -> bool:
    model = 'gpt-4'
    messages = [{"role": "system",
                 "content": "Please inspect the following csv data rows to help determine if the first row is a special header row describing the other rows or just another data row."}]    
    for ix, row in enumerate(rows[:20]):
        messages.append({"role": "user", "content": f'row {ix}: {row}'})
    messages.append({"role": "user", "content": "Is the first row a header row describing the other rows or just another data row? Output 'header' or 'data'."})
    completion = get_chat_completion(messages, temperature=0, model=model)
    if 'header' in completion.lower():
        return True
    return False
    