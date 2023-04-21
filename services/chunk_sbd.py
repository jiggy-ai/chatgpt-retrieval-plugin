import pysbd
from typing import Callable     

def chunk_text_pysbd(text           : str, 
                     target_tokens  : int, 
                     tokenizer_func : Callable, 
                     language       : str, 
                     pdf            : bool = False) -> list[str]:
    """
    use pysbd to break a text into chunks around target_tokens length.
    """    
    doc_type = "pdf" if pdf else None    
    language = language if language else "en"
    segmenter = pysbd.Segmenter(language=language, clean=True, doc_type=doc_type)

    current_lines = []
    current_tokens = []
    sum_current_tokens = 0    
    
    for s in segmenter.segment(text):        
        s_tokens = len(tokenizer_func(s))
        if sum_current_tokens + s_tokens//2 > target_tokens:
            yield " ".join(current_lines)
            overlap = 2 if len(current_lines) > 10 else 1
            current_lines  =  current_lines[-overlap : ] 
            current_tokens = current_tokens[-overlap : ]
            sum_current_tokens = sum(current_tokens)
        sum_current_tokens += s_tokens
        current_lines.append(s)
        current_tokens.append(s_tokens)
        
    yield " ".join(current_lines)