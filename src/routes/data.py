from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from models import ResponseSignal
import os
import logging
import aiofiles
from controllers import DataController, ProjectController, ProcessController
from .schemas.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.db_schemas import DataChunk

logger = logging.getLogger('uvicorn.error ')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"]
)

@data_router.post("/upload/{project_id}")
async def upload_file(request: Request,project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):

    prject_model = ProjectModel(request.app.db_client)

    project = await prject_model.get_project_or_create_one(project_id)


    data_controller = DataController()

    is_valid, validation_message = data_controller.validate_uploaded_file(file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": validation_message}
        )

    project_dir_path = ProjectController().get_project_path(project_id)
    file_path, unique_filename = data_controller.generate_uniuqe_filepath(file.filename, project_id)

    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):  # Read the file in chunks
                await out_file.write(chunk)
    except Exception as e:
        logger.error(f"Error while uploading file: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.FILE_UPLOAD_FAILED.value}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value, "file_id": unique_filename}
    )

@data_router.post("/process/{project_id}")
async def process_file(request: Request,project_id: str, process_request: ProcessRequest):
    process_controller = ProcessController(project_id)
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    prject_model = ProjectModel(request.app.db_client)
    
    project = await prject_model.get_project_or_create_one(project_id=project_id)

    try:
        file_content = process_controller.get_file_content(file_id)
        chunks = process_controller.process_file_content(file_content, file_id, chunk_size, overlap_size)

        # Here you can implement the logic to store the chunks in a database or any other storage.
        # For demonstration purposes, we'll just return the number of chunks created.
        if chunks is None or len(chunks) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.PROCESSING_FAILED.value}
            )
        
        file_chunk_records = [
            DataChunk(
                chunk_metadata=chunk.metadata,
                chunk_text=chunk.page_content,
                chunk_order=i+1,
                chunk_project_id=project.id
            )
            for i, chunk in enumerate(chunks)
        ]
        chunk_model = ChunkModel(request.app.db_client)

        if do_reset == 1:
            _ = await chunk_model.delete_chunks_by_project_id(
                project.id
            )

        no_records = await chunk_model.insert_many_chunks(file_chunk_records)

        return JSONResponse(
            content={
                "signal": ResponseSignal.PROCESSING_SUCCESS.value,
                "inserted chunks": no_records
            }
        )
        
    
    except Exception as e:
        logger.error(f"Error while processing file: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.PROCESSING_FAILED.value}
        )