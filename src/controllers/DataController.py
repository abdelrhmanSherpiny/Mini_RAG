from .BaseController import BaseController
from .ProjectController import ProjectController
from fastapi import UploadFile
from models import ResponseSignal
import os
import re

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576 # 1 MB in bytes

    def validate_uploaded_file(self, file:UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

        if file.size > self.size_scale * self.app_settings.FILE_MAX_SIZE:
            return False, ResponseSignal.FILE_SIZE_EXCEEDED.value

        return True, ResponseSignal.FILE_VALIDATED_SUCCESS.value

    def generate_uniuqe_filepath(self, orig_file_name:str, project_id:str):

        random_str = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id)

        cleaned_filename = self.get_cleaned_filename(orig_file_name)
        unique_filename = f"{random_str}_{cleaned_filename}"
        unique_filepath = os.path.join(project_path, unique_filename)

        while os.path.exists(unique_filepath):
            random_str = self.generate_random_string()
            unique_filename = f"{random_str}_{cleaned_filename}"
            unique_filepath = os.path.join(project_path, unique_filename)
        return unique_filepath, unique_filename



    def get_cleaned_filename(self, filename:str):
        # Remove any special characters and spaces from the filename
        cleaned_filename = re.sub(r'[^\w.]', '', filename.strip())
        cleaned_filename = cleaned_filename.replace(" ", "_")  # Replace spaces with underscores    
        return cleaned_filename