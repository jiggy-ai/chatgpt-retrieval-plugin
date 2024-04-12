from loguru import logger
from models.models import Source
from services.openai import get_chat_completion
import json
from typing import Dict
from server.config import extract_metadata_config
from pydantic import BaseModel, Field, validator
from typing import Optional
from services.pydantic_completion import pydantic_completion
from datetime import datetime

class BasicDocumentMetadata(BaseModel):
    title:      str           = Field(description="The title of the document content. " \
                                                  "This is a required field.  " \
                                                  "If there is no clear title specified in the content " \
                                                  "please output a good title for the content based on the available info including the filename. ")
    author:     Optional[str] = Field(default=None, description="The author or entity that created the document content.")

    created_at: Optional[str] = Field(default=None, description="The date in the ISO 8501 format (YYYY-MM-DD) that the content was created if it appears in the content.  " \
                                                                "Can also be the copyright date.")
    language:   Optional[str] = Field(default="en", description="The 2 character ISO 639-1 language code of the primary language of the content.")
    
    @validator("created_at")
    def validate_iso_date(cls, value):
        if value is None or value == "":
            return None
        try:
            datetime.fromisoformat(value)
            return value
        except ValueError as e:
            logger.warning(e)
            raise ValueError(f"created_at string must be in ISO format YYYY-MM-DD: {e}")


def extract_metadata_from_document(text: str, filename : str = "unknown") -> Dict[str, str]:

    #model = 'gpt-3.5-turbo'
    model = "gpt-4-turbo-2024-04-09"
    initial_text = text[:2048]   + " <truncated>"  # use first 2048 characters of text
    logger.info(f"Extracting metadata from document filename {filename} using model {model} and first 2048 characters of text")
    logger.info(f"Initial text: {initial_text}")
    
    messages = [{"role":   "user",
                "content": "Please extract the requested metadata from the following document content:"},
                {"role":   "user",
                "content": f"filename: {filename}"},
                {"role":   "user",
                "content": initial_text}]
    try:
        metadata = pydantic_completion(messages, BasicDocumentMetadata, model=model, retry=3)
        logger.info(f"Extracted metadata: {metadata}")
    except Exception as e:
        logger.exception(e)
        metadata = BasicDocumentMetadata(title='unknown', language = 'en')
    
    return metadata.dict()
        





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
    