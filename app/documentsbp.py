from flask import Blueprint, jsonify, request, current_app
from .mongodb_models import Booking, User
from . import mongo
from bson import ObjectId
from .authbp import token_required
from .storage_service import get_storage_service
import os
import hashlib
import hmac
import time
import json
from datetime import datetime, timedelta
import traceback
import requests
from werkzeug.utils import secure_filename
import zipfile
import io
import urllib.parse

documentsbp = Blueprint("documentsbp", __name__)

# Configuration constants
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_PER_BOOKING = 20

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_copyparty_config():
    """Get Copyparty configuration from the copyparty manager."""
    try:
        # Import here to avoid circular imports
        from copyparty_manager import copyparty_manager
        config = copyparty_manager.config
        return {
            'base_url': config['base_url'],
            'api_token': config['api_token'],
            'upload_password': config['upload_password'],
            'folder_prefix': config['folder_prefix']
        }
    except ImportError:
        # Fallback to environment variables if copyparty_manager is not available
        current_app.logger.warning("Copyparty manager not available, using environment variables")
        return {
            'base_url': os.getenv('COPYPARTY_BASE_URL', 'http://localhost:3923'),
            'api_token': os.getenv('COPYPARTY_API_TOKEN'),
            'upload_password': os.getenv('COPYPARTY_UPLOAD_PASSWORD'),
            'folder_prefix': os.getenv('COPYPARTY_FOLDER_PREFIX', 'bookings')
        }

def generate_share_token(booking_id, categories, expires_in_seconds=604800):
    """Generate a secure share token for client access."""
    import secrets

    # Generate a short random token ID
    token_id = secrets.token_urlsafe(16)  # Short, URL-safe token
    expires_at = int(time.time()) + expires_in_seconds

    return token_id, expires_at

def verify_share_token(token):
    """Verify and decode a share token."""
    try:
        # Look up token in database
        share_record = mongo.db.share_tokens.find_one({"token": token})

        if not share_record:
            current_app.logger.error(f"Share token not found: {token}")
            return None

        # Check expiration
        if share_record['expires_at'] < datetime.utcnow():
            current_app.logger.error(f"Share token expired: {token}")
            return None

        # Return payload format expected by the endpoint
        return {
            'booking_id': str(share_record['booking_id']),
            'categories': share_record['categories'],
            'expires_at': int(share_record['expires_at'].timestamp())
        }
    except Exception as e:
        current_app.logger.error(f"Error verifying share token: {str(e)}")
        return None

def upload_to_copyparty(file, booking_id, category, original_filename):
    """Upload file to Copyparty server."""
    config = get_copyparty_config()

    # Generate unique filename with booking info
    timestamp = int(time.time())
    safe_filename = secure_filename(original_filename)
    unique_filename = f"{booking_id}_{category}_{timestamp}_{safe_filename}"

    # Prepare upload URL (upload to root)
    upload_url = f"{config['base_url']}/"

    # Read file content first
    file.seek(0)
    file_content = file.read()
    file.seek(0)

    # Prepare files and data for upload (Copyparty format)
    files = {'f': (unique_filename, file_content, file.content_type)}
    data = {'act': 'bput'}

    # Add authentication if available
    if config['api_token']:
        data['token'] = config['api_token']
    elif config['upload_password']:
        data['password'] = config['upload_password']

    try:
        response = requests.post(upload_url, files=files, data=data, timeout=30)
        response.raise_for_status()

        # Return file info
        return {
            'url': f"{config['base_url']}/{unique_filename}",
            'filename': unique_filename,
            'original_filename': original_filename,
            'path': unique_filename,
            'size': len(file_content)
        }
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error uploading to Copyparty: {str(e)}")
        raise Exception(f"Upload failed: {str(e)}")

@documentsbp.route("/api/bookings/<booking_id>/documents", methods=["GET"])
@token_required
def get_documents(current_user, booking_id):
    """Get all documents for a booking."""
    try:
        current_app.logger.info(f"User {current_user['username']} requesting documents for booking {booking_id}")

        # Verify booking exists and user has access
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        # Check permissions (booking owner or admin)
        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access"}), 403

        # Get documents from database
        documents = list(mongo.db.booking_documents.find({"booking_id": ObjectId(booking_id)}))
        current_app.logger.info(f"Found {len(documents)} documents for booking {booking_id}")

        # Convert to response format
        documents_data = []
        for doc in documents:
            documents_data.append({
                "id": str(doc['_id']),
                "filename": doc['filename'],
                "category": doc['category'],
                "size": doc['size'],
                "uploadedAt": doc['uploaded_at'].isoformat(),
                "url": doc['url'],
                "mimeType": doc['mime_type'],
                "bookingId": str(doc['booking_id'])
            })

        # Get itinerary URL
        itinerary_url = booking.get('itinerary_url', '')

        return jsonify({
            "documents": documents_data,
            "itineraryUrl": itinerary_url
        })

    except Exception as e:
        error_msg = f"Error fetching documents: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@documentsbp.route("/api/bookings/<booking_id>/documents", methods=["POST"])
@token_required
def upload_document(current_user, booking_id):
    """Upload a document for a booking."""
    try:
        current_app.logger.info(f"User {current_user['username']} uploading document for booking {booking_id}")

        # Verify booking exists and user has access
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        # Check permissions
        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access"}), 403

        # Check if file is present
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Validate file
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"}), 400

        # Check number of existing documents
        existing_count = mongo.db.booking_documents.count_documents({"booking_id": ObjectId(booking_id)})
        if existing_count >= MAX_FILES_PER_BOOKING:
            return jsonify({"error": f"Maximum {MAX_FILES_PER_BOOKING} files allowed per booking"}), 400

        # Get category from form data
        category = request.form.get('category', 'Other')
        if category not in ['Voucher', 'Air Ticket', 'Invoice', 'Other']:
            category = 'Other'

        # Upload using storage service (Copyparty with GCS fallback)
        upload_result = get_storage_service().upload_file(file, booking_id, category, file.filename)

        # Save document metadata to database
        document = {
            "booking_id": ObjectId(booking_id),
            "filename": upload_result['original_filename'],
            "stored_filename": upload_result['filename'],
            "category": category,
            "size": upload_result['size'],
            "mime_type": file.content_type,
            "url": upload_result['url'],
            "path": upload_result['path'],
            "storage_type": upload_result['storage_type'],
            "uploaded_at": datetime.utcnow(),
            "uploaded_by": ObjectId(current_user['_id'])
        }

        result = mongo.db.booking_documents.insert_one(document)
        document['_id'] = result.inserted_id

        current_app.logger.info(f"Document uploaded successfully: {upload_result['filename']}")

        # Return document info
        return jsonify({
            "document": {
                "id": str(document['_id']),
                "filename": document['filename'],
                "category": document['category'],
                "size": document['size'],
                "uploadedAt": document['uploaded_at'].isoformat(),
                "url": document['url'],
                "mimeType": document['mime_type'],
                "bookingId": str(document['booking_id'])
            }
        })

    except Exception as e:
        error_msg = f"Error uploading document: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Upload failed"}), 500

@documentsbp.route("/api/bookings/<booking_id>/documents/<document_id>", methods=["PUT"])
@token_required
def update_document(current_user, booking_id, document_id):
    """Update document metadata (e.g., category)."""
    try:
        # Verify booking exists and user has access
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access"}), 403

        # Get document
        document = mongo.db.booking_documents.find_one({
            "_id": ObjectId(document_id),
            "booking_id": ObjectId(booking_id)
        })

        if not document:
            return jsonify({"error": "Document not found"}), 404

        # Get update data
        data = request.get_json()
        update_data = {}

        if 'category' in data and data['category'] in ['Voucher', 'Air Ticket', 'Invoice', 'Other']:
            update_data['category'] = data['category']

        if update_data:
            mongo.db.booking_documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )

        return jsonify({"message": "Document updated successfully"})

    except Exception as e:
        error_msg = f"Error updating document: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": "Update failed"}), 500

@documentsbp.route("/api/bookings/<booking_id>/documents/<document_id>", methods=["DELETE"])
@token_required
def delete_document(current_user, booking_id, document_id):
    """Delete a document."""
    try:
        # Verify booking exists and user has access
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access"}), 403

        # Get document
        document = mongo.db.booking_documents.find_one({
            "_id": ObjectId(document_id),
            "booking_id": ObjectId(booking_id)
        })

        if not document:
            return jsonify({"error": "Document not found"}), 404

        # TODO: Delete from Copyparty (optional - could be left for cleanup)
        # For now, just delete from database
        mongo.db.booking_documents.delete_one({"_id": ObjectId(document_id)})

        return jsonify({"message": "Document deleted successfully"})

    except Exception as e:
        error_msg = f"Error deleting document: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": "Delete failed"}), 500

@documentsbp.route("/api/bookings/<booking_id>/itinerary", methods=["PUT"])
@token_required
def update_itinerary_url(current_user, booking_id):
    """Update the itinerary URL for a booking."""
    try:
        # Verify booking exists and user has access
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access"}), 403

        # Get URL from request
        data = request.get_json()
        itinerary_url = data.get('url', '')

        # Update booking with itinerary URL
        mongo.db.bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"itinerary_url": itinerary_url}}
        )

        return jsonify({"message": "Itinerary URL updated successfully"})

    except Exception as e:
        error_msg = f"Error updating itinerary URL: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": "Update failed"}), 500

@documentsbp.route("/api/bookings/<booking_id>/share", methods=["GET"])
@token_required
def get_existing_share_link(current_user, booking_id):
    """Get existing active share link for a booking."""
    try:
        # Verify booking exists and user has access
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access"}), 403

        # Find the most recent non-expired share token for this booking
        current_time = datetime.utcnow()
        share_record = mongo.db.share_tokens.find_one({
            "booking_id": ObjectId(booking_id),
            "expires_at": {"$gt": current_time}
        }, sort=[("created_at", -1)])

        if not share_record:
            return jsonify({"error": "No active share link found"}), 404

        # Create share URL
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        share_url = f"{frontend_url}/share/{share_record['token']}"

        return jsonify({
            "token": share_record['token'],
            "shareUrl": share_url,
            "expiresAt": share_record['expires_at'].isoformat(),
            "allowedCategories": share_record['categories'],
            "createdAt": share_record['created_at'].isoformat(),
            "usedCount": share_record.get('used_count', 0)
        })

    except Exception as e:
        error_msg = f"Error fetching share link: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": "Failed to fetch share link"}), 500

@documentsbp.route("/api/bookings/<booking_id>/share", methods=["POST"])
@token_required
def generate_share_link(current_user, booking_id):
    """Generate a secure share link for client access."""
    try:
        # Verify booking exists and user has access
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access"}), 403

        # Get request data
        data = request.get_json()
        categories = data.get('categories', ['Voucher', 'Air Ticket'])
        expires_in_seconds = data.get('expiresInSeconds', 604800)  # 7 days default

        # Generate token
        token, expires_at = generate_share_token(booking_id, categories, expires_in_seconds)

        # Create share URL
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        share_url = f"{frontend_url}/share/{token}"

        # Store share token in database for tracking
        share_record = {
            "booking_id": ObjectId(booking_id),
            "token": token,
            "categories": categories,
            "expires_at": datetime.fromtimestamp(expires_at),
            "created_at": datetime.utcnow(),
            "created_by": ObjectId(current_user['_id']),
            "used_count": 0
        }

        mongo.db.share_tokens.insert_one(share_record)

        return jsonify({
            "token": token,
            "shareUrl": share_url,
            "expiresAt": datetime.fromtimestamp(expires_at).isoformat(),
            "categories": categories
        })

    except Exception as e:
        error_msg = f"Error generating share link: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": "Failed to generate share link"}), 500

@documentsbp.route("/share/<token>", methods=["GET"])
def view_shared_documents(token):
    """Public endpoint for clients to access shared documents."""
    try:
        # Verify token
        payload = verify_share_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired link"}), 403

        booking_id = payload['booking_id']
        allowed_categories = payload['categories']

        # Get booking info
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        # Get documents for allowed categories
        current_app.logger.info(f"Looking for documents with booking_id: {booking_id}, categories: {allowed_categories}")

        documents = list(mongo.db.booking_documents.find({
            "booking_id": ObjectId(booking_id),
            "category": {"$in": allowed_categories}
        }))

        current_app.logger.info(f"Found {len(documents)} documents for sharing")

        # Convert to response format (without internal URLs for security)
        documents_data = []
        for doc in documents:
            documents_data.append({
                "id": str(doc['_id']),
                "filename": doc['filename'],
                "category": doc['category'],
                "size": doc['size'],
                "uploadedAt": doc['uploaded_at'].isoformat(),
                "downloadUrl": f"/api/share/{token}/download/{doc['_id']}"
            })

        # Update usage count
        mongo.db.share_tokens.update_one(
            {"token": token},
            {"$inc": {"used_count": 1}}
        )

        return jsonify({
            "booking": {
                "name": booking['name'],
                "id": str(booking['_id'])
            },
            "documents": documents_data,
            "allowedCategories": allowed_categories,
            "expiresAt": datetime.fromtimestamp(payload['expires_at']).isoformat()
        })

    except Exception as e:
        error_msg = f"Error accessing shared documents: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": "Access failed"}), 500

@documentsbp.route("/api/share/<token>", methods=["GET"])
def api_view_shared_documents(token):
    """API endpoint alias for shared documents access."""
    return view_shared_documents(token)

@documentsbp.route("/api/share/<token>/download/<documentId>", methods=["GET"])
def download_shared_document(token, documentId):
    """Download a specific document via share link."""
    try:
        current_app.logger.info(f"Download request for token: {token}, documentId: {documentId}")

        # Verify token
        payload = verify_share_token(token)
        if not payload:
            current_app.logger.error(f"Invalid or expired token: {token}")
            return jsonify({"error": "Invalid or expired link"}), 403

        booking_id = payload['booking_id']
        allowed_categories = payload['categories']
        current_app.logger.info(f"Token valid for booking: {booking_id}, categories: {allowed_categories}")

        # Get document
        document = mongo.db.booking_documents.find_one({
            "_id": ObjectId(documentId),
            "booking_id": ObjectId(booking_id),
            "category": {"$in": allowed_categories}
        })

        if not document:
            current_app.logger.error(f"Document not found: {documentId} for booking: {booking_id}")
            return jsonify({"error": "Document not found or not allowed"}), 404

        current_app.logger.info(f"Found document: {document['filename']}, URL: {document['url']}")

        # Download file using storage service
        try:
            file_content, content_type = get_storage_service().download_file(
                document['url'],
                document.get('storage_type', 'copyparty')
            )

            current_app.logger.info(f"Successfully fetched file, size: {len(file_content)} bytes")

            # Fallback content type detection if needed
            if not content_type or content_type == 'application/octet-stream':
                filename = document['filename'].lower()
                if filename.endswith('.pdf'):
                    content_type = 'application/pdf'
                elif filename.endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif filename.endswith('.png'):
                    content_type = 'image/png'
                elif filename.endswith('.docx'):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

            # Create response with file content
            from flask import Response

            response = Response(
                file_content,
                content_type=content_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{document["filename"]}"',
                    'Content-Length': str(len(file_content)),
                    'Cache-Control': 'no-cache'
                }
            )

            # Update usage count
            mongo.db.share_tokens.update_one(
                {"token": token},
                {"$inc": {"used_count": 1}}
            )

            current_app.logger.info(f"Streaming file: {document['filename']}")
            return response

        except Exception as e:
            current_app.logger.error(f"Failed to fetch file from storage: {e}")
            return jsonify({"error": "File not accessible"}), 503

    except Exception as e:
        error_msg = f"Error downloading shared document: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Download failed"}), 500

@documentsbp.route("/api/share/<token>/download-all", methods=["GET"])
def download_all_shared_documents(token):
    """Download all documents for a share link as a zip file."""
    try:
        # Verify token
        payload = verify_share_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired link"}), 403

        booking_id = payload['booking_id']
        allowed_categories = payload['categories']

        # Get booking info
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        # Get documents for allowed categories
        documents = list(mongo.db.booking_documents.find({
            "booking_id": ObjectId(booking_id),
            "category": {"$in": allowed_categories}
        }))

        if not documents:
            return jsonify({"error": "No documents found"}), 404

        current_app.logger.info(f"Creating zip file for {len(documents)} documents")

        # Create a zip file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for doc in documents:
                try:
                    # Download file using storage service
                    file_content, _ = get_storage_service().download_file(
                        doc['url'],
                        doc.get('storage_type', 'copyparty')
                    )

                    # Add file to zip with original filename
                    # Use category prefix to organize files in zip
                    safe_filename = secure_filename(doc['filename'])
                    zip_filename = f"{doc['category']}/{safe_filename}"

                    zip_file.writestr(zip_filename, file_content)
                    current_app.logger.info(f"Added {safe_filename} to zip")

                except Exception as e:
                    current_app.logger.error(f"Failed to add {doc.get('filename', 'unknown')} to zip: {e}")
                    # Continue with other files even if one fails
                    continue

        zip_buffer.seek(0)

        # Generate filename for the zip
        safe_booking_name = secure_filename(booking.get('name', 'booking'))
        zip_filename = f"{safe_booking_name}_documents.zip"

        # Update usage count
        mongo.db.share_tokens.update_one(
            {"token": token},
            {"$inc": {"used_count": 1}}
        )

        # Return the zip file
        from flask import send_file
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )

    except Exception as e:
        error_msg = f"Error creating zip download: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Download failed"}), 500