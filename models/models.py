from pydantic import BaseModel, Field
from typing import List, Optional, Union
from enum import Enum
import uuid
import json 


class Source(str, Enum):
    email = "email"
    file = "file"
    chat = "chat"
    web  = "web"


class DocumentMetadata(BaseModel):
    source: Optional[Source] = None
    source_id: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Union[str, List[str]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = Field(description="The 2 character ISO 639-1 language code of the primary language of the content.")
    version: str = None

    @classmethod
    def __get_validators__(cls):
        yield cls.custom_validate

    @classmethod
    def custom_validate(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        if isinstance(value, dict):
            return cls(**value)
        return value

    
class DocumentChunkMetadata(DocumentMetadata):
    document_id: str


class DocumentChunk(BaseModel):
    id: str
    doc_id: Optional[str]
    text: str
    metadata: DocumentChunkMetadata
    embedding: Optional[List[float]] = None
    token_count: Optional[int] = None
    reference_url: Optional[str] = None
    
    def __str__(self):
        if len(self.text) > 100:
            text = self.text[:100] + '...'
        else: 
            text = self.text
        text = text.replace('\n', ' ')
        estr = "DocumentChunk("
        if self.id is not None:
            estr += f"id={self.id}, "
        if self.metadata is not None:
            estr += f"metadata={str(self.metadata)}, "
        if self.embedding is not None:
            estr += f"embedding=dim{len(self.embedding)}, "
        estr += f"text={text})"
        return estr


class DocumentChunkWithScore(DocumentChunk):
    score: float


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: Optional[DocumentMetadata] = None
    mimetype: Optional[str] = None
    token_count: Optional[int] = None
    
class DocumentWithChunks(Document):
    chunks: List[DocumentChunk]


class DocumentMetadataFilter(BaseModel):
    document_id: Optional[str] = None
    source: Optional[Source] = None
    source_id: Optional[str] = None
    author: Optional[str] = None
    start_date: Optional[str] = None  # any date string format
    end_date: Optional[str] = None  # any date string format
    title: Optional[str] = None
    url: Optional[str] = None


class Query(BaseModel):
    query: str = Field(..., min_length=1)
    filter: Optional[DocumentMetadataFilter] = None
    top_k: Optional[int] = 7

class QueryWithEmbedding(Query):
    embedding: List[float]


class QueryResult(BaseModel):
    query: str
    results: List[DocumentChunkWithScore]
