"""
Appwrite REST API helper.

This helper wraps the Appwrite REST API using httpx. It keeps dependencies
lightweight (no Appwrite SDK required for now) and focuses on the endpoints we
need for NotesStore operations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

import config


class AppwriteClient:
    def __init__(self) -> None:
        if not config.APPWRITE_ENDPOINT or not config.APPWRITE_PROJECT_ID:
            raise RuntimeError("Appwrite endpoint/project missing. Set APPWRITE_* env vars.")
        if not config.APPWRITE_API_KEY:
            raise RuntimeError("APPWRITE_API_KEY is required for backend operations.")
        self._base = config.APPWRITE_ENDPOINT.rstrip("/")
        self._project = config.APPWRITE_PROJECT_ID
        self._api_key = config.APPWRITE_API_KEY

    def _headers(self, content_type: Optional[str] = "json") -> Dict[str, str]:
        headers = {
            "X-Appwrite-Project": self._project,
            "X-Appwrite-Key": self._api_key,
        }
        if content_type == "json":
            headers["Content-Type"] = "application/json"
        return headers

    def create_document(self, collection_id: str, document_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base}/databases/{config.APPWRITE_DATABASE_ID}/collections/{collection_id}/documents"
        payload = {"documentId": document_id, "data": data}
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    def update_document(self, collection_id: str, document_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base}/databases/{config.APPWRITE_DATABASE_ID}/collections/{collection_id}/documents/{document_id}"
        payload = {"data": data}
        with httpx.Client(timeout=15) as client:
            resp = client.patch(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    def get_document(self, collection_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self._base}/databases/{config.APPWRITE_DATABASE_ID}/collections/{collection_id}/documents/{document_id}"
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    def list_documents(
        self,
        collection_id: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self._base}/databases/{config.APPWRITE_DATABASE_ID}/collections/{collection_id}/documents"
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            params["cursorDirection"] = "after"
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    def delete_document(self, collection_id: str, document_id: str) -> None:
        url = f"{self._base}/databases/{config.APPWRITE_DATABASE_ID}/collections/{collection_id}/documents/{document_id}"
        with httpx.Client(timeout=15) as client:
            resp = client.delete(url, headers=self._headers())
            if resp.status_code not in (200, 204, 404):
                resp.raise_for_status()

    def upload_file(self, bucket_id: str, filename: str, data: bytes, mime: str) -> str:
        url = f"{self._base}/storage/buckets/{bucket_id}/files"
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                url,
                headers=self._headers(content_type=None),
                data={"fileId": "unique()"},
                files={"file": (filename, data, mime)},
            )
            resp.raise_for_status()
            body = resp.json()
            return body.get("$id") or body.get("fileId") or ""

    def delete_file(self, bucket_id: str, file_id: str) -> None:
        url = f"{self._base}/storage/buckets/{bucket_id}/files/{file_id}"
        with httpx.Client(timeout=30) as client:
            resp = client.delete(url, headers=self._headers())
            if resp.status_code not in (200, 204, 404):
                resp.raise_for_status()

    def download_file(self, bucket_id: str, file_id: str) -> bytes:
        url = f"{self._base}/storage/buckets/{bucket_id}/files/{file_id}/download"
        with httpx.Client(timeout=60) as client:
            resp = client.get(url, headers=self._headers(content_type=None))
            resp.raise_for_status()
            return resp.content
