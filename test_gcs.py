"""
Simple test script to verify Google Cloud Storage credentials are working.
"""
import os
import sys
import json
from google.cloud import storage

# Force UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_gcs_connection():
    """Test GCS connection and credentials."""
    try:
        # Get credentials from environment
        creds_json = os.getenv('GCS_CREDENTIALS_JSON')
        project_id = os.getenv('GCS_PROJECT_ID', 'divine-actor-473706-k4')
        bucket_name = os.getenv('GCS_BUCKET_NAME', 'bks_file_upload_bucket')

        if not creds_json:
            print("❌ ERROR: GCS_CREDENTIALS_JSON environment variable not set")
            return False

        print("✓ Found GCS_CREDENTIALS_JSON in environment")

        # Parse JSON
        try:
            credentials_info = json.loads(creds_json)
            print("✓ Successfully parsed credentials JSON")
            print(f"  Project ID: {credentials_info.get('project_id')}")
            print(f"  Client Email: {credentials_info.get('client_email')}")
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to parse credentials JSON: {e}")
            return False

        # Initialize client
        print("\nInitializing GCS client...")
        client = storage.Client.from_service_account_info(
            credentials_info,
            project=project_id
        )
        print("✓ GCS client initialized successfully")

        # Test bucket access
        print(f"\nTesting access to bucket: {bucket_name}")
        bucket = client.bucket(bucket_name)

        # Check if bucket exists
        if bucket.exists():
            print(f"✓ Successfully accessed bucket: {bucket_name}")
        else:
            print(f"❌ ERROR: Bucket does not exist: {bucket_name}")
            return False

        # List some blobs (files) in the bucket
        print("\nListing files in bucket (up to 5):")
        blobs = list(bucket.list_blobs(max_results=5))
        if blobs:
            for blob in blobs:
                print(f"  - {blob.name} ({blob.size} bytes)")
        else:
            print("  (bucket is empty)")

        # Test write permission by creating a test file
        print("\nTesting write permission...")
        test_blob = bucket.blob("test_connection.txt")
        test_blob.upload_from_string("GCS connection test successful!")
        print("✓ Successfully uploaded test file")

        # Test read permission
        print("\nTesting read permission...")
        content = test_blob.download_as_text()
        print(f"✓ Successfully read test file: {content}")

        # Clean up test file
        print("\nCleaning up test file...")
        test_blob.delete()
        print("✓ Successfully deleted test file")

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED - GCS credentials are working!")
        print("="*50)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        if load_dotenv():
            print("✓ Loaded environment variables from .env file\n")
        else:
            print("⚠ No .env file found, using system environment variables\n")
    except ImportError:
        print("⚠ python-dotenv not installed, using system environment variables\n")

    success = test_gcs_connection()
    exit(0 if success else 1)