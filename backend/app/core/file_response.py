"""
Resilient On-Disk File Streaming (Backend Core Module).

Serves files that live on disk (tracking artifacts, uploaded source clips) in a
way that guarantees the response body always matches the headers that describe
it.

Architectural Role:
- Core infrastructure helper used by the API presentation tier.
- Removes the `Content-Length` / body mismatch failure mode of Starlette's
  `FileResponse`, which aborts the connection whenever the file changes
  between the `os.stat()` call and the streamed read.
- Keeps large payloads off the event loop by dispatching every read to a
  worker thread.

Notes:
- Starlette 0.37 `FileResponse` advertises the size observed by `os.stat()` and
  then re-opens the file to stream it. If the file is rewritten in between -
  which happens whenever an artifact is still being produced - the body ends up
  longer than the advertised length. uvicorn then raises
  `RuntimeError: Response content longer than Content-Length`, drops the
  connection, and the browser reports the download as failed.
- Opening the file first and sizing the payload from the open file descriptor
  removes that race: the advertised length describes the exact byte stream that
  is subsequently sent, and the payload is clamped to it.
"""

import os
from typing import AsyncIterator, BinaryIO
from urllib.parse import quote

import anyio
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

# Number of bytes written to the socket per chunk while streaming a file.
CHUNK_SIZE = 64 * 1024


def _content_disposition(filename: str) -> str:
    """
    Build a `Content-Disposition` header value that offers the file as a download.

    Args:
        filename: Download name presented to the browser.

    Returns:
        Header value string with the ASCII fallback and the RFC 5987 form.
    """
    quoted = quote(filename)
    if quoted != filename:
        return f"attachment; filename*=utf-8''{quoted}"
    return f'attachment; filename="{filename}"'


async def _iter_file_chunks(handle: BinaryIO, length: int) -> AsyncIterator[bytes]:
    """
    Yield at most `length` bytes from an already opened binary file handle.

    Args:
        handle: Open binary file handle positioned at the start of the file.
        length: Maximum number of bytes to yield.

    Yields:
        Chunks of file content, never exceeding `length` bytes in total.

    Notes:
        Reads are dispatched to a worker thread so a large artifact never
        blocks the event loop. The handle is always closed once the response
        has been streamed, or the client disconnected mid-transfer.
    """
    remaining = length
    try:
        while remaining > 0:
            chunk = await anyio.to_thread.run_sync(
                handle.read, min(CHUNK_SIZE, remaining)
            )
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        handle.close()


def stream_file_response(path: str, media_type: str, filename: str) -> StreamingResponse:
    """
    Stream a file from disk with a response that can never contradict itself.

    Args:
        path: Absolute path of the file to serve.
        media_type: MIME type advertised for the payload.
        filename: Download name presented to the browser.

    Returns:
        StreamingResponse that sends exactly the number of bytes it declares.

    Raises:
        OSError: If the file cannot be opened.
    """
    handle = open(path, "rb")
    try:
        # Size the payload from the open descriptor rather than from the path:
        # it describes the exact byte stream that will be read, not whatever
        # the path happens to point at once the response is written.
        length = os.fstat(handle.fileno()).st_size
    except OSError:
        handle.close()
        raise

    return StreamingResponse(
        _iter_file_chunks(handle, length),
        media_type=media_type,
        headers={
            "content-length": str(length),
            "content-disposition": _content_disposition(filename),
        },
        background=BackgroundTask(handle.close),
    )
