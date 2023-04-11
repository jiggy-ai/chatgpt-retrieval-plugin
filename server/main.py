from loguru import logger
import sys
import uvicorn
from fastapi import FastAPI, File, HTTPException, Depends, Body, UploadFile, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from typing import Optional
from services.extract_metadata import extract_metadata_from_document
from server.config import HOSTNAME, plugin_config, auth_tokens, plugin_auth, PluginAuthType, service_config, ServiceConfig, sub_access
from server.auth import verified_sub
from fastapi.openapi.utils import get_openapi
import yaml
import json
import copy


from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
    DocumentChunk,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file


logger.remove()
logger.add(sys.stderr, level="INFO", format="{level}: [{name}:{function}:{line}] {message}")

bearer_scheme = HTTPBearer()
def validate_plugin_token_bearer(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials not in auth_tokens.authorized_tokens:
        logger.info(f"Invalid or missing token with scheme {credentials.scheme}")
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials

def validate_subscriber_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    sub = verified_sub(credentials)
    if sub not in sub_access.read:
        logger.info(f"Unauthorized subscriber {sub}")
        raise HTTPException(status_code=403, detail="Unauthorized")
    return credentials

def validate_subscriber_write_permission(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    sub = verified_sub(credentials)
    if sub not in sub_access.write:
        logger.info(f"Unauthorized subscriber {sub}")
        raise HTTPException(status_code=403, detail="Unauthorized")
    return credentials


app = FastAPI()

if plugin_auth == PluginAuthType.bearer:
    logger.info("Plugin API: bearer token auth")
    plugin_dependencies = [Depends(validate_plugin_token_bearer)]
elif plugin_auth == PluginAuthType.none:
    logger.info("Plugin API: Open (No auth)")
    plugin_dependencies = []
elif plugin_auth == PluginAuthType.oauth:    
    logger.info("Plugin API: Oauth")
    plugin_dependencies = [Depends(validate_subscriber_token)]
else:
    logger.error(f"Invalid plugin_auth value {plugin_auth}")
    raise ValueError(f"Invalid plugin_auth value {plugin_auth}")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/plugin/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.1",
    servers=[{"url": f"https://{HOSTNAME}.gpt-gateway.com/plugin"}],
    dependencies=plugin_dependencies,
)
app.mount("/plugin", sub_app)

app.mount("/.well-known", StaticFiles(directory="/code/.well-known"), name="static")




@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
    dependencies=[Depends(validate_subscriber_write_permission)],    
)
async def upsert_file(
    file: UploadFile = File(...),
):
    logger.info(f"Received file {file.filename}")
    try:
        document = await get_document_from_file(file)        
        ids = await datastore.upsert([document])        
        return UpsertResponse(ids=ids)
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))            
    except Exception as e:
        logger.error("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post(
    "/upsert",
    response_model=UpsertResponse,
    dependencies=[Depends(validate_subscriber_write_permission)],
)
async def upsert(
    request: UpsertRequest = Body(...),        
):
    logger.info(f"{len(request.documents)} documents")
    try:
        for document in request.documents:
            # attempt to extract metadata if any of our 3 extracted metadata fields are missing
            if not {'created_at', 'title', 'author'}.issubset(document.metadata.dict(exclude_none=True)):
                extracted_metadata = extract_metadata_from_document(document.text)
                for k, v in extracted_metadata.items():
                    if k not in document.metadata.dict():  # don't overwrite existing metadata
                        logger.info(f"Adding metadata {k}={v}")
                        document.metadata[k] = v                    
        ids = await datastore.upsert(request.documents)
        return UpsertResponse(ids=ids)
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))    
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
    dependencies=[Depends(validate_subscriber_token)],        
)
async def query_main(
    request: QueryRequest = Body(...),
):
    logger.info(request)
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))    
    except Exception as e:
        logger.error("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.get(
    "/docs/{doc_id}",
    response_model=list[DocumentChunk],
    dependencies=[Depends(validate_subscriber_token)],        
)
async def docs(doc_id: str = Path(..., description="The document ID to get" )):
    logger.info(doc_id)
    try:
        results = await datastore.doc(doc_id)
        return results
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))        
    except Exception as e:
        logger.error("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")



@app.get(
    "/chunks",
    response_model=list[DocumentChunk],
    dependencies=[Depends(validate_subscriber_token)],        
)
async def chunks(start: Optional[int] = Query(default=0, description="Offset of the first result to return"),
                 limit: Optional[int] = Query(default=10, description="Number of results to return starting from the offset"),
                 reverse: Optional[bool] = Query(default=True, description="Reverse the order of the items")):
    logger.info(f"start {start}, limit {limit}, reverse {reverse}")
    try:
        results = await datastore.chunks(start, limit, reverse)
        return results
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))        
    except Exception as e:
        logger.error("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")




@sub_app.post(
    "/query",
    response_model=QueryResponse,    
    response_model_exclude_none=True,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
):
    logger.info(request)
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))        
    except Exception as e:
        logger.error("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
    dependencies=[Depends(validate_subscriber_write_permission)],    
)
async def delete(
    request: DeleteRequest = Body(...),
):
    logger.info(request)
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        return DeleteResponse(success=success)
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))        
    except Exception as e:
        logger.error("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@app.get(
    '/config',     
    dependencies=[Depends(validate_subscriber_token)],        
)
def get_config() -> ServiceConfig:
    # copy the config and remove the auth tokens
    c = copy.deepcopy(service_config)
    c.auth_tokens = []
    return c    


import server.oauth_proxy    # add additional endpoints post app creation

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()
    logger.info("Startup complete")
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutdown")
    datastore.shutdown()
    logger.info("Shutdown complete")
    
# update .well-known specs to match current config
from pydantic.networks import AnyUrl, url_regex
def _any_url_representer(dumper, data):
    return dumper.represent_scalar("!anyurl", str(data))
yaml.add_representer(AnyUrl, _any_url_representer)
# omitted the constructor for AnyUrl since it is not required here
yaml.add_implicit_resolver("!anyurl", url_regex())
with open("/code/.well-known/openapi.yaml", "w") as output_file:
    output_file.write(yaml.dump(sub_app.openapi(), sort_keys=False, allow_unicode=True))
with open("/code/.well-known/ai-plugin.json", "w") as output_file:
    output_file.write(json.dumps(plugin_config.dict(), indent=4, sort_keys=False))


#def start():
#    logger.info("Start")
#    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
#    logger.info("Start done")

if __name__ == "__main__":
    logger.info("Start")
    uvicorn.run(app,
                host="0.0.0.0",
                port=8080,
                log_level="debug",
                reload=False)
    logger.info("uvicorn done")