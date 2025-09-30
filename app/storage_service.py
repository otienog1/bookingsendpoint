"""
Storage service module that handles file operations with fallback support.
Supports Copyparty as primary and Google Cloud Storage as fallback.
"""
import os
import time
import requests
from werkzeug.utils import secure_filename
from flask import current_app
from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError
import json
from typing import Optional, Dict, Any, Tuple, BinaryIO


class StorageService:
    """Unified storage service with Copyparty primary and GCS fallback."""

    def __init__(self):
        self.copyparty_config = self._get_copyparty_config()
        self.gcs_config = self._get_gcs_config()
        self.gcs_client = None
        self._init_gcs_client()

    def _get_copyparty_config(self) -> Dict[str, Any]:
        """Get Copyparty configuration."""
        try:
            # Try to import copyparty manager first
            from copyparty_manager import copyparty_manager
            config = copyparty_manager.config
            return {
                'base_url': config['base_url'],
                'api_token': config['api_token'],
                'upload_password': config['upload_password'],
                'folder_prefix': config['folder_prefix']
            }
        except ImportError:
            # Fallback to environment variables
            return {
                'base_url': os.getenv('COPYPARTY_BASE_URL', 'http://localhost:3923'),
                'api_token': os.getenv('COPYPARTY_API_TOKEN'),
                'upload_password': os.getenv('COPYPARTY_UPLOAD_PASSWORD'),
                'folder_prefix': os.getenv('COPYPARTY_FOLDER_PREFIX', 'bookings')
            }

    def _get_gcs_config(self) -> Dict[str, Any]:
        """Get Google Cloud Storage configuration."""
        return {
            'bucket_name': os.getenv('GCS_BUCKET_NAME', 'bks_file_upload_bucket'),
            'folder_prefix': os.getenv('GCS_FOLDER_PREFIX', 'copyparty'),
            'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
            'credentials_json': os.getenv('GCS_CREDENTIALS_JSON'),
            'project_id': os.getenv('GCS_PROJECT_ID')
        }

    def _init_gcs_client(self):
        """Initialize Google Cloud Storage client."""
        try:
            if self.gcs_config['credentials_json']:
                # Use JSON credentials from environment variable
                credentials_info = json.loads(self.gcs_config['credentials_json'])
                self.gcs_client = storage.Client.from_service_account_info(
                    credentials_info,
                    project=self.gcs_config['project_id']
                )
            elif self.gcs_config['credentials_path']:
                # Use credentials file path
                self.gcs_client = storage.Client.from_service_account_json(
                    self.gcs_config['credentials_path'],
                    project=self.gcs_config['project_id']
                )
            elif self.gcs_config['project_id']:
                # Use default credentials (for Google Cloud environments)
                self.gcs_client = storage.Client(project=self.gcs_config['project_id'])
            else:
                current_app.logger.warning("No GCS credentials configured. GCS fallback disabled.")
                self.gcs_client = None
        except Exception as e:
            current_app.logger.error(f"Failed to initialize GCS client: {e}")
            self.gcs_client = None

    def _test_copyparty_connection(self) -> bool:
        """Test if Copyparty is accessible."""
        try:
            response = requests.get(
                f"{self.copyparty_config['base_url']}/",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            current_app.logger.warning(f"Copyparty connection test failed: {e}")
            return False

    def _upload_to_copyparty(self, file: BinaryIO, booking_id: str, category: str, original_filename: str) -> Dict[str, Any]:
        """Upload file to Copyparty server."""
        # Generate unique filename with booking info
        timestamp = int(time.time())
        safe_filename = secure_filename(original_filename)
        unique_filename = f"{booking_id}_{category}_{timestamp}_{safe_filename}"

        # Prepare upload URL (upload to root)
        upload_url = f"{self.copyparty_config['base_url']}/"

        # Read file content
        file.seek(0)
        file_content = file.read()
        file.seek(0)

        # Prepare files and data for upload (Copyparty format)
        files = {'f': (unique_filename, file_content, file.content_type)}
        data = {'act': 'bput'}

        # Add authentication if available
        if self.copyparty_config['api_token']:
            data['token'] = self.copyparty_config['api_token']
        elif self.copyparty_config['upload_password']:
            data['password'] = self.copyparty_config['upload_password']

        response = requests.post(upload_url, files=files, data=data, timeout=30)
        response.raise_for_status()

        return {
            'url': f"{self.copyparty_config['base_url']}/{unique_filename}",
            'filename': unique_filename,
            'original_filename': original_filename,
            'path': unique_filename,
            'size': len(file_content),
            'storage_type': 'copyparty'
        }

    def _upload_to_gcs(self, file: BinaryIO, booking_id: str, category: str, original_filename: str) -> Dict[str, Any]:
        """Upload file to Google Cloud Storage."""
        if not self.gcs_client:
            raise Exception("GCS client not initialized")

        # Generate unique filename with booking info
        timestamp = int(time.time())
        safe_filename = secure_filename(original_filename)
        unique_filename = f"{booking_id}_{category}_{timestamp}_{safe_filename}"

        # Create blob path with folder prefix
        blob_path = f"{self.gcs_config['folder_prefix']}/{unique_filename}"

        # Get bucket and create blob
        bucket = self.gcs_client.bucket(self.gcs_config['bucket_name'])
        blob = bucket.blob(blob_path)

        # Read file content
        file.seek(0)
        file_content = file.read()
        file.seek(0)

        # Upload to GCS
        blob.upload_from_string(
            file_content,
            content_type=file.content_type
        )

        # Make blob publicly readable (optional, adjust based on your security needs)
        # blob.make_public()

        return {
            'url': f"gs://{self.gcs_config['bucket_name']}/{blob_path}",
            'public_url': blob.public_url if hasattr(blob, 'public_url') else None,
            'filename': unique_filename,
            'original_filename': original_filename,
            'path': blob_path,
            'size': len(file_content),
            'storage_type': 'gcs'
        }

    def upload_file(self, file: BinaryIO, booking_id: str, category: str, original_filename: str) -> Dict[str, Any]:
        """
        Upload file with fallback support.
        Tries Copyparty first, falls back to GCS if Copyparty fails.
        """
        current_app.logger.info(f"Attempting to upload file: {original_filename}")

        # Try Copyparty first
        if self._test_copyparty_connection():
            try:
                result = self._upload_to_copyparty(file, booking_id, category, original_filename)
                current_app.logger.info(f"File uploaded to Copyparty: {original_filename}")
                return result
            except Exception as e:
                current_app.logger.warning(f"Copyparty upload failed: {e}")
        else:
            current_app.logger.warning("Copyparty is not accessible")

        # Fallback to GCS
        if self.gcs_client:
            try:
                result = self._upload_to_gcs(file, booking_id, category, original_filename)
                current_app.logger.info(f"File uploaded to GCS: {original_filename}")
                return result
            except Exception as e:
                current_app.logger.error(f"GCS upload failed: {e}")
                raise Exception(f"Both Copyparty and GCS upload failed. Last error: {e}")
        else:
            raise Exception("No storage backend available. Copyparty failed and GCS not configured.")

    def download_file(self, file_url: str, storage_type: str = None) -> Tuple[bytes, str]:
        """
        Download file from storage.
        Returns (file_content, content_type)
        """
        if storage_type == 'gcs' or file_url.startswith('gs://'):
            return self._download_from_gcs(file_url)
        else:
            # Assume Copyparty or try both
            try:
                return self._download_from_copyparty(file_url)
            except Exception as e:
                current_app.logger.warning(f"Copyparty download failed: {e}")
                # Try GCS if URL might be a GCS URL
                if 'storage.googleapis.com' in file_url or file_url.startswith('gs://'):
                    return self._download_from_gcs(file_url)
                raise

    def _download_from_copyparty(self, file_url: str) -> Tuple[bytes, str]:
        """Download file from Copyparty."""
        response = requests.get(file_url, timeout=30, stream=True)
        response.raise_for_status()

        content_type = response.headers.get('content-type', 'application/octet-stream')
        file_content = response.content

        return file_content, content_type

    def _download_from_gcs(self, file_url: str) -> Tuple[bytes, str]:
        """Download file from Google Cloud Storage."""
        if not self.gcs_client:
            raise Exception("GCS client not initialized")

        # Parse GCS URL
        if file_url.startswith('gs://'):
            # Format: gs://bucket_name/path/to/file
            url_parts = file_url[5:].split('/', 1)
            bucket_name = url_parts[0]
            blob_path = url_parts[1] if len(url_parts) > 1 else ''
        else:
            # Assume it's a path in our configured bucket
            bucket_name = self.gcs_config['bucket_name']
            blob_path = file_url

        bucket = self.gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        if not blob.exists():
            raise Exception(f"File not found in GCS: {file_url}")

        file_content = blob.download_as_bytes()
        content_type = blob.content_type or 'application/octet-stream'

        return file_content, content_type


# Global storage service instance
storage_service = StorageService()