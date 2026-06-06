"""
Uploads scored_stocks.json to Google Drive.
Authenticates using the GDRIVE_SERVICE_ACCOUNT_JSON environment variable.
"""

import json
import logging
import os
import tempfile
from datetime import date
from io import BytesIO

logger = logging.getLogger(__name__)


def _build_service():
    """Build and return an authenticated Google Drive service client."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_json = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise EnvironmentError("GDRIVE_SERVICE_ACCOUNT_JSON environment variable not set")

    sa_info = json.loads(sa_json)
    credentials = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    return service


def _find_file(service, name: str, parent_id: str) -> str | None:
    """Return the file ID of `name` in `parent_id`, or None if not found."""
    query = f"name='{name}' and '{parent_id}' in parents and trashed=false"
    resp = service.files().list(q=query, fields="files(id, name)").execute()
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def _find_or_create_folder(service, folder_name: str, parent_id: str) -> str:
    """Return the folder ID of `folder_name` inside `parent_id`, creating it if needed."""
    query = (
        f"name='{folder_name}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    resp = service.files().list(q=query, fields="files(id)").execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def _upload_or_update(service, name: str, content: bytes, parent_id: str, mime_type: str = "application/json"):
    """Upload a new file or update an existing one in `parent_id`."""
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(BytesIO(content), mimetype=mime_type, resumable=False)
    existing_id = _find_file(service, name, parent_id)

    if existing_id:
        service.files().update(
            fileId=existing_id,
            media_body=media,
        ).execute()
        logger.info("Updated '%s' (id=%s) in Drive", name, existing_id)
    else:
        metadata = {"name": name, "parents": [parent_id]}
        f = service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
        ).execute()
        logger.info("Created '%s' (id=%s) in Drive", name, f["id"])


def upload_to_drive(scored_stocks: list[dict]) -> bool:
    """
    Upload scored_stocks.json to the Drive folder specified by GDRIVE_FOLDER_ID.
    Also uploads a dated snapshot to a history/ subfolder.
    Returns True on success, False on failure.
    """
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        logger.error("GDRIVE_FOLDER_ID environment variable not set — skipping Drive upload")
        return False

    try:
        service = _build_service()
    except Exception as e:
        logger.error("Failed to authenticate with Google Drive: %s", e)
        return False

    payload = json.dumps(scored_stocks, indent=2, default=str).encode("utf-8")

    try:
        # Upload / overwrite main file
        _upload_or_update(service, "scored_stocks.json", payload, folder_id)

        # Dated snapshot in history/
        history_folder_id = _find_or_create_folder(service, "history", folder_id)
        dated_name = f"{date.today().isoformat()}_scored_stocks.json"
        _upload_or_update(service, dated_name, payload, history_folder_id)

        logger.info("Google Drive upload complete")
        return True

    except Exception as e:
        logger.error("Google Drive upload failed: %s", e)
        return False
