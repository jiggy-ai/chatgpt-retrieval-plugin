from loguru import logger
import os
import uvicorn
from fastapi import FastAPI, File, HTTPException, Depends, Body, UploadFile, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from typing import Optional

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
from services.extract_metadata import extract_metadata_from_document

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)


@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
):
    logger.info(f"Received file {file.filename}")
    document = await get_document_from_file(file)

    extracted_metadata = extract_metadata_from_document(document.text)
    for k, v in extracted_metadata.items():
        if k not in document.metadata.dict():
            logger.info(f"Adding metadata {k}={v}")
            document.metadata[k] = v
    try:
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
)
async def upsert(
    request: UpsertRequest = Body(...),
):
    logger.info(f"{len(request.documents)} documents")
    try:
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


@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
