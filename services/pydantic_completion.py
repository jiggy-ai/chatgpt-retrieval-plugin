"""
Wrapper around OpenAI ChatCompletion that compels the language model to produce a valid Pydantic model as output via prompting and iterative error remediation.  The easiest way to go from unstructured text to structured Pydantic data.

It uses the pydantic json_schema to help guide the model to the required output format.

It will retry the task with error messages if the model does not produce appropriate output data due to either a json load issue or a pydantic validation issue.

"""

from loguru import logger
from pydantic import BaseModel, ValidationError
from typing import List, Tuple
import openai
import json 


def pydantic_completion(messages : List[dict], model_class: BaseModel, retry=3, temperature=0, **kwargs) -> BaseModel:

    messages.append({"role"   : "system",
                     "content": f"Please respond ONLY with valid json that conforms to this pydantic json_schema: {model_class.schema_json()}. Do not include additional text other than the object json as we will load this object with json.loads() and pydantic."})

    last_exception = None
    for i in range(retry+1):
        try:
            response = openai.ChatCompletion.create(messages=messages, temperature=temperature, **kwargs)
        except Exception as e:
            logger.warning(f"openai.ChatCompletion.create exception: {e}")
            if i == retry:
                raise e
            continue
            
        assistant_message= response['choices'][0]['message']
        content = assistant_message['content']
        try:
            json_content = json.loads(content)
        except Exception as e:
            last_exception = e
            error_msg = f"json.loads exception: {e}"
            logger.error(error_msg)
            messages.append(assistant_message)
            messages.append({"role"   : "system",
                            "content": error_msg})
            continue
        try:
            return model_class(**json_content)
        except Exception as e:
            last_exception = e
            error_msg = f"pydantic exception: {e}"
            logger.info(json_content)
            logger.error(error_msg)
            messages.append(assistant_message)            
            messages.append({"role"   : "system",
                            "content": error_msg})    
    raise last_exception
