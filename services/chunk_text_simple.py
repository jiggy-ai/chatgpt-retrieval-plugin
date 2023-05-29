from loguru import logger
from typing import List, Optional
from server.config import chunk_config
import tiktoken

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





def get_text_chunks(text: str, chunk_token_size: Optional[int]) -> List[str]:
    """
    Split a text into chunks of ~CHUNK_SIZE tokens, based on punctuation and newline boundaries.

    Args:
        text: The text to split into chunks.
        chunk_token_size: The target size of each chunk in tokens, or None to use the default CHUNK_SIZE.

    Returns:
        A list of text chunks, each of which is a string of ~CHUNK_SIZE tokens.
    """
    # Return an empty list if the text is empty or whitespace
    if not text or text.isspace():
        return []

    # Tokenize the text
    tokens = tokenizer.encode(text, disallowed_special=())

    # Initialize an empty list of chunks
    chunks = []

    # Use the provided chunk token size or the default one
    chunk_size = chunk_token_size or CHUNK_SIZE

    # Initialize a counter for the number of chunks
    num_chunks = 0

    # Loop until all tokens are consumed
    while tokens and num_chunks < MAX_NUM_CHUNKS:
        # Take the first chunk_size tokens as a chunk
        chunk = tokens[:chunk_size]

        # Decode the chunk into text
        chunk_text = tokenizer.decode(chunk)

        # Skip the chunk if it is empty or whitespace
        if not chunk_text or chunk_text.isspace():
            # Remove the tokens corresponding to the chunk text from the remaining tokens
            tokens = tokens[len(chunk) :]
            # Continue to the next iteration of the loop
            continue

        # Find the last period or punctuation mark in the chunk
        last_punctuation = max(
            chunk_text.rfind("."),
            chunk_text.rfind("?"),
            chunk_text.rfind("!"),
            chunk_text.rfind("\n"),
        )

        # If there is a punctuation mark, and the last punctuation index is before MIN_CHUNK_SIZE_CHARS
        if last_punctuation != -1 and last_punctuation > MIN_CHUNK_SIZE_CHARS:
            # Truncate the chunk text at the punctuation mark
            chunk_text = chunk_text[: last_punctuation + 1]

        # Remove any newline characters and strip any leading or trailing whitespace
        chunk_text_to_append = chunk_text.replace("\n", " ").strip()

        if len(chunk_text_to_append) > MIN_CHUNK_LENGTH_TO_EMBED:
            # Append the chunk text to the list of chunks
            chunks.append(chunk_text_to_append)

        # Remove the tokens corresponding to the chunk text from the remaining tokens
        tokens = tokens[len(tokenizer.encode(chunk_text, disallowed_special=())) :]

        # Increment the number of chunks
        num_chunks += 1
        
    if num_chunks == MAX_NUM_CHUNKS:
        logger.warning(f"Reached the maximum number of chunks ({MAX_NUM_CHUNKS}) for text of length {len(text)}")
        
    # Handle the remaining tokens
    if tokens:
        remaining_text = tokenizer.decode(tokens).replace("\n", " ").strip()
        if len(remaining_text) > MIN_CHUNK_LENGTH_TO_EMBED:
            chunks.append(remaining_text)

    return chunks
