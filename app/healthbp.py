from flask import Blueprint, jsonify, current_app
from .storage_service import get_storage_service
import os

healthbp = Blueprint("healthbp", __name__)

@healthbp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify system status."""
    try:
        status = {
            "status": "healthy",
            "environment": {
                "flask_env": os.getenv('FLASK_ENV', 'not_set'),
                "gcs_project_id": os.getenv('GCS_PROJECT_ID', 'not_set'),
                "gcs_bucket_name": os.getenv('GCS_BUCKET_NAME', 'not_set'),
                "gcs_credentials_available": bool(os.getenv('GCS_CREDENTIALS_JSON') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
                "copyparty_url": os.getenv('COPYPARTY_BASE_URL', 'not_set')
            },
            "storage": {}
        }

        # Test storage service initialization
        try:
            storage_service = get_storage_service()
            status["storage"]["service_initialized"] = True
            status["storage"]["gcs_client_available"] = storage_service.gcs_client is not None
            status["storage"]["copyparty_accessible"] = storage_service._test_copyparty_connection()

            if storage_service.gcs_client:
                # Test GCS access
                try:
                    bucket_name = storage_service.gcs_config['bucket_name']
                    bucket = storage_service.gcs_client.bucket(bucket_name)
                    bucket.reload()
                    status["storage"]["gcs_bucket_accessible"] = True
                except Exception as e:
                    status["storage"]["gcs_bucket_accessible"] = False
                    status["storage"]["gcs_error"] = str(e)
            else:
                status["storage"]["gcs_bucket_accessible"] = False
                status["storage"]["gcs_error"] = "GCS client not initialized"

        except Exception as e:
            status["storage"]["service_initialized"] = False
            status["storage"]["error"] = str(e)
            current_app.logger.error(f"Storage service health check failed: {e}")

        return jsonify(status)

    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@healthbp.route("/storage-test", methods=["GET"])
def storage_test():
    """Test storage service functionality."""
    try:
        storage_service = get_storage_service()

        result = {
            "gcs_client": storage_service.gcs_client is not None,
            "copyparty_connection": storage_service._test_copyparty_connection(),
            "gcs_config": {
                "bucket_name": storage_service.gcs_config['bucket_name'],
                "project_id": storage_service.gcs_config['project_id'],
                "folder_prefix": storage_service.gcs_config['folder_prefix'],
                "has_credentials_json": bool(storage_service.gcs_config['credentials_json']),
                "has_credentials_path": bool(storage_service.gcs_config['credentials_path'])
            }
        }

        if storage_service.gcs_client:
            # Test bucket access
            try:
                bucket = storage_service.gcs_client.bucket(storage_service.gcs_config['bucket_name'])
                bucket.reload()
                result["gcs_bucket_access"] = True
            except Exception as e:
                result["gcs_bucket_access"] = False
                result["gcs_bucket_error"] = str(e)

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Storage test failed: {e}")
        return jsonify({
            "error": str(e)
        }), 500