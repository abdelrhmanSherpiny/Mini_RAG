from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from models import ResponseSignal
import os
import logging
import aiofiles
from controllers import DataController, ProjectController, ProcessController
from .schemas.data import ProcessRequest

logger = logging.getLogger('uvicorn.error ')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"]
)

@data_router.post("/upload/{project_id}")
async def upload_file(project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):
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
async def process_file(project_id: str, request: ProcessRequest):
    process_controller = ProcessController(project_id)
    file_id = request.file_id
    chunk_size = request.chunk_size
    overlap_size = request.overlap_size
    do_reset = request.do_reset

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
        
        return chunks  # Return the chunks as a response for demonstration purposes
        
    
    except Exception as e:
        logger.error(f"Error while processing file: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.PROCESSING_FAILED.value}
        )