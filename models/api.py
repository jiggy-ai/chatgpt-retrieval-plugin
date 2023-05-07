from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryResult,
    DocumentChunk,
)
from pydantic import BaseModel, Field
from typing import List, Optional


class UpsertRequest(BaseModel):
    documents: List[Document]


class UpsertResponse(BaseModel):
    ids: List[str]


class QueryRequest(BaseModel):
    queries: List[Query]


class QueryResponse(BaseModel):
    results: List[QueryResult]


class DeleteRequest(BaseModel):
    ids: Optional[List[str]] = None
    filter: Optional[DocumentMetadataFilter] = None
    delete_all: Optional[bool] = False


class DeleteResponse(BaseModel):
    success: bool

class Accounting(BaseModel):
    chunk_count: int
    doc_count: int
    page_count: int


class DocChunksResponse(BaseModel):
    docs       : list[list[DocumentChunk]] = Field(..., description="A list of documents, each containing a list of chunks")
    next_index : int                       = Field(..., description="The index of the next document to return.  Use this value as the index parameter in the next request to get the next set of documents")  
      