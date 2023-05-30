from loguru import logger
import pysbd
from typing import Callable, Tuple     
from server.config import chunk_config
from services.chunk_text_simple import get_text_chunks

MAX_NUM_CHUNKS = chunk_config.max_num_chunks             # The maximum number of chunks to generate from a text

def chunk_text_pysbd(text           : str, 
                     target_tokens  : int, 
                     tokenizer_func : Callable, 
                     language       : str, 
                     pdf            : bool = False,
                     max_tokens     : int  = 1024) -> Tuple[list[str], list[int]]:
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
       
    segments       = [s for s in segmenter.segment(text)]
    segment_tokens = [len(tokenizer_func(s)) for s in segments]

    # the sbd sometimes outputs huge chunks of text for stuff like tables that have no real sentence structure
    # in this case we fall back to the simple chunker to break those up
    def subchunk():
        for s, s_tokens in zip(segments, segment_tokens):    
            if s_tokens < max_tokens:
                yield s, s_tokens
            else:
                for text, tokens in get_text_chunks(s, max_tokens):
                    yield text, tokens
                    
    for s, s_tokens in subchunk():
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
    