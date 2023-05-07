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


class DocChunksRequest(BaseModel):
    index              : int = Field(-1,    description="The index of the first document to return.  Use 0 to start at the beginning.  Use -1 to start at the end.")
    limit              : int = Field(10,    description="The maximum number of documents to return")
    max_chunks_per_doc : int = Field(1,     description="The maximum number of chunks to return per document")
    reverse            : bool = Field(True, description="If true, return documents in reverse order with most recent First.")

class DocChunksResponse(BaseModel):
    docs       : list[list[DocumentChunk]] = Field(..., description="A list of documents, each containing a list of chunks")
    next_index : int                       = Field(..., description="The index of the next document to return.  Use this value as the index parameter in the next request to get the next set of documents")  
      