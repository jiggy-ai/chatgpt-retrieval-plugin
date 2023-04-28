from loguru import logger
import pysbd
from typing import Callable, Tuple     
from server.config import chunk_config

MAX_NUM_CHUNKS = chunk_config.max_num_chunks             # The maximum number of chunks to generate from a text

def chunk_text_pysbd(text           : str, 
                     target_tokens  : int, 
                     tokenizer_func : Callable, 
                     language       : str, 
                     pdf            : bool = False) -> Tuple[list[str], list[int]]:
    """
    use pysbd to break a text into chunks around target_tokens length.
    return (list of chunks, list of token counts for each chunk)
    """    
    doc_type = "pdf" if pdf else None    
    language = language if language else "en"
    segmenter = pysbd.Segmenter(language=language, clean=True, doc_type=doc_type)
    
    result_chunks = []
    result_token_counts = []

    current_lines = []
    current_tokens = []
    sum_current_tokens = 0        
    for s in segmenter.segment(text):        
        s_tokens = len(tokenizer_func(s))
        if sum_current_tokens + s_tokens//2 > target_tokens:
            result_chunks.append(" ".join(current_lines))
            result_token_counts.append(sum(current_tokens))
            overlap = 2 if len(current_lines) > 10 else 1
            current_lines  =  current_lines[-overlap : ] 
            current_tokens = current_tokens[-overlap : ]
            sum_current_tokens = sum(current_tokens)
            if len(result_chunks) >= MAX_NUM_CHUNKS:
                logger.warning(f"Reached the maximum number of chunks ({MAX_NUM_CHUNKS}) for text of length {len(text)}")
                current_lines = current_tokens = []
                break
        sum_current_tokens += s_tokens
        current_lines.append(s)
        current_tokens.append(s_tokens)

    result_chunks.append(" ".join(current_lines))
    result_token_counts.append(sum(current_tokens))
    return result_chunks, result_token_counts
    