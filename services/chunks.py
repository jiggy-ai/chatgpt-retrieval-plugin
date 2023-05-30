from loguru import logger
from typing import Dict, List, Optional, Tuple
from models.models import Document, DocumentChunk, DocumentChunkMetadata
from server.config import chunk_config
from services.chunk_sbd import chunk_text_pysbd
import tiktoken
from services.file import excel_mimetypes
from services.openai import get_embeddings
from services.chunk_text_simple import get_text_chunks

# Global variables
tokenizer = tiktoken.get_encoding(
    "cl100k_base"
)  # The encoding scheme to use for tokenization


# Set constants from chunk_config
logger.info(chunk_config)
CHUNK_SIZE                = chunk_config.chunk_size                 # The target size of each text chunk in tokens
MIN_CHUNK_SIZE_CHARS      = chunk_config.min_chunk_size_chars       # The minimum size of each text chunk in characters
MIN_CHUNK_LENGTH_TO_EMBED = chunk_config.min_chunk_length_to_embed  # Discard chunks shorter than this
EMBEDDINGS_BATCH_SIZE     = chunk_config.embeddings_batch_size      # The number of embeddings to request at a time
MAX_NUM_CHUNKS            = chunk_config.max_num_chunks             # The maximum number of chunks to generate from a text




def get_csv_chunks(records : list[str], max_tokens : int):
    chunks = []
    tokens = []
    for record in records:
        token_count = len(tokenizer.encode(record, disallowed_special=()))
        if token_count > CHUNK_SIZE:
            chars = len(record)
            tokens_per_char = token_count / chars
            max_chars = int(max_tokens / tokens_per_char)
            # split the record into chunks of less than max_chars
            for i in range(0, len(record), max_chars):
                chunk = record[i:i+max_chars]
                chunks.append(chunk)
                token_count = len(tokenizer.encode(chunk, disallowed_special=()))
                tokens.append(token_count)
        else:
            chunks.append(record)
            tokens.append(token_count)

    return chunks, tokens
                                
    
    
    
def create_document_chunks(
    doc: Document, chunk_token_size: Optional[int]
) -> Tuple[List[DocumentChunk], str]:
    """
    Create a list of document chunks from a document object and return the document id.

    Args:
        doc: The document object to create chunks from. It should have a text attribute and optionally an id and a metadata attribute.
        chunk_token_size: The target size of each chunk in tokens, or None to use the default CHUNK_SIZE.

    Returns:
        A tuple of (doc_chunks, doc_id), where doc_chunks is a list of document chunks, each of which is a DocumentChunk object with an id, a document_id, a text, and a metadata attribute,
        and doc_id is the id of the document object. The id of each chunk is generated from the document id and a sequential number, and the metadata is copied from the document object.
    """
    # Check if the document text is empty or whitespace
    if not doc.text or doc.text.isspace():
        return [], doc.id

    # Split the document text into chunks
    # text_chunks = get_text_chunks(doc.text, chunk_token_size)
    chunk_token_size = chunk_token_size or CHUNK_SIZE
    if doc.mimetype in ['text/csv']+excel_mimetypes:
        logger.info(f"Splitting {doc.mimetype} into chunks on record boundaries")
        text_chunks, token_counts = get_csv_chunks(doc.text.split('\n'), max_tokens=2000)
    else:
        logger.info(f"Splitting {doc.mimetype} '{doc.metadata.language}' language document into chunks of size {chunk_token_size}")
        try:
            text_chunks, token_counts =  chunk_text_pysbd(text           = doc.text,
                                                          target_tokens  = chunk_token_size,                                    
                                                          tokenizer_func = tokenizer.encode,
                                                          language       = doc.metadata.language,
                                                          pdf            = doc.mimetype == 'application/pdf')
        except Exception as e:
            logger.error(f"pysbd failed to split {doc.mimetype} '{doc.metadata.language}' language document into chunks of size {chunk_token_size}: ({e})")
            text_chunks, token_counts = get_text_chunks(doc.text, chunk_token_size)
            
    total_tokens = sum(token_counts)
    logger.info(f"Split document {doc.id} into {len(text_chunks)} chunks with a total of {total_tokens} tokens")
    doc.token_count = total_tokens
                
    metadata = (
        DocumentChunkMetadata(document_id = doc.id,
                              **doc.metadata.__dict__)
        if doc.metadata is not None
        else DocumentChunkMetadata(document_id = doc.id)
    )

    # Initialize an empty list of chunks for this document
    doc_chunks = []

    # Assign each chunk a sequential number and create a DocumentChunk object
    for i, (text_chunk, token_count) in enumerate(zip(text_chunks, token_counts)):
        chunk_id = f"{doc.id}_{i}"
        doc_chunk = DocumentChunk(
            id=chunk_id,
            text=text_chunk,
            metadata=metadata,
            token_count = token_count,
        )
        # Append the chunk object to the list of chunks for this document
        doc_chunks.append(doc_chunk)

    # Return the list of chunks and the document id
    return doc_chunks, doc.id


def get_document_chunks(
    documents: List[Document], chunk_token_size: Optional[int]
) -> Dict[str, List[DocumentChunk]]:
    """
    Convert a list of documents into a dictionary from document id to list of document chunks.

    Args:
        documents: The list of documents to convert.
        chunk_token_size: The target size of each chunk in tokens, or None to use the default CHUNK_SIZE.

    Returns:
        A dictionary mapping each document id to a list of document chunks, each of which is a DocumentChunk object
        with text, metadata, and embedding attributes.
    """
    # Initialize an empty dictionary of lists of chunks
    chunks: Dict[str, List[DocumentChunk]] = {}

    # Initialize an empty list of all chunks
    all_chunks: List[DocumentChunk] = []

    # Loop over each document and create chunks
    for doc in documents:
        doc_chunks, doc_id = create_document_chunks(doc, chunk_token_size)

        # Append the chunks for this document to the list of all chunks
        all_chunks.extend(doc_chunks)

        # Add the list of chunks for this document to the dictionary with the document id as the key
        chunks[doc_id] = doc_chunks

    # Check if there are no chunks
    if not all_chunks:
        return {}

    # Get all the embeddings for the document chunks in batches, using get_embeddings
    embeddings: List[List[float]] = []

    def headerize(chunk: DocumentChunk) -> str:
        prefix = ""
        if chunk.metadata.source_id:
            prefix += f'{chunk.metadata.source_id}: '        
        if chunk.metadata.title:
            prefix += f'{chunk.metadata.title}: '
        if chunk.metadata.author:
            prefix += f'{chunk.metadata.author}: '            
        return prefix + chunk.text
    
    for i in range(0, len(all_chunks), EMBEDDINGS_BATCH_SIZE):
        # Get the text of the chunks in the current batch
        batch_texts = [headerize(chunk) for chunk in all_chunks[i : i + EMBEDDINGS_BATCH_SIZE]]
        # Get the embeddings for the batch texts
        batch_embeddings = get_embeddings(batch_texts)

        # Append the batch embeddings to the embeddings list
        embeddings.extend(batch_embeddings)

    # Update the document chunk objects with the embeddings
    for i, chunk in enumerate(all_chunks):
        # Assign the embedding from the embeddings list to the chunk object
        chunk.embedding = embeddings[i]

    return chunks
