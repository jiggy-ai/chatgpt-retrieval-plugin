from loguru import logger
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import asyncio

from models.models import (
    Document,
    DocumentChunk,
    DocumentMetadataFilter,
    Query,
    QueryResult,
    QueryWithEmbedding,
)
from services.chunks import get_document_chunks
from services.openai import get_embeddings

        
class DataStore(ABC):
    async def upsert(
        self, documents: List[Document], chunk_token_size: Optional[int] = None
    ) -> List[str]:
        """
        Takes in a list of documents and inserts them into the database.
        First deletes all the existing vectors with the document id (if necessary, depends on the vector db), then inserts the new ones.
        Return a list of document ids.
        """
        # Delete any existing vectors for documents with the input document ids
        await asyncio.gather(
            *[
                self.delete(
                    filter=DocumentMetadataFilter(
                        document_id=document.id,
                    ),
                    delete_all=False,
                )
                for document in documents
                if document.id
            ]
        )
        chunks = get_document_chunks(documents, chunk_token_size)
        if not chunks:
            raise ValueError("No useable content found in documents")
        return await self._upsert(chunks)

    @abstractmethod
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """

        raise NotImplementedError

    async def query(self, queries: List[Query]) -> List[QueryResult]:
        """
        Takes in a list of queries and filters and returns a list of query results with matching document chunks and scores.
        """
        # get a list of of just the queries from the Query list
        query_texts = [query.query for query in queries]
        query_embeddings = get_embeddings(query_texts)
        # hydrate the queries with embeddings
        queries_with_embeddings = [
            QueryWithEmbedding(**query.dict(), embedding=embedding)
            for query, embedding in zip(queries, query_embeddings)
        ]
        return await self._query(queries_with_embeddings)

    @abstractmethod
    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        raise NotImplementedError

    async def chunks(self, start: int, limit: int, reverse :bool) -> List[DocumentChunk]:
        """
        Returns a list of document chunks from the datastore based on the start, limit, and reverse parameters.
        """
        return await self._chunks(start, limit, reverse)

    @abstractmethod
    async def _chunks(self, start: int, limit: int, reverse :bool) -> List[DocumentChunk]:
        """
        Returns a list of document chunks from the datastore based on the start, limit, and reverse parameters.
        """
        raise NotImplementedError


    async def doc(self, doc_id) -> List[DocumentChunk]:
        """
        Returns a list of document chunks from the datastore based on the doc_id
        """
        return await self._doc(doc_id)

    @abstractmethod
    async def _doc(self, doc_id) -> List[DocumentChunk]:
        """
        Returns a list of document chunks from the datastore based on the doc_id
        """
        raise NotImplementedError

    
    @abstractmethod
    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Multiple parameters can be used at once.
        Returns whether the operation was successful.
        """
        raise NotImplementedError

    @abstractmethod
    def shutdown(self):
        """
        prepare for shutdown    
        """
        raise NotImplementedError
