from fastapi import FastAPI, UploadFile, File, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import re
import httpx
from typing import Optional, Iterator
from src.main import main as process_main
from src.anaglyph_processor import main_anaglyph
from uuid import uuid4


APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Use environment variables for Render deployment
INPUT_DIR = os.getenv("INPUT_DIR", os.path.join(APP_DIR, "input"))
OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", os.path.join(APP_DIR, "output"))
STREAM_DIR = os.path.join(OUTPUTS_DIR, "stream")

def _find_hls_dir() -> str:
    # Prefer top-level output/stream; fall back to src/output/stream (used by pipeline)
    candidates = [
        os.path.join(APP_DIR, "output", "stream"),
        os.path.join(APP_DIR, "src", "output", "stream"),
    ]
    for d in candidates:
        if os.path.isdir(d):
            return d
    # Default to first path; created on demand later by pipeline
    return candidates[0]

HLS_DIR = _find_hls_dir()


app = FastAPI(title="VR 180 Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Ensure base dirs exist at startup and mount HLS
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(STREAM_DIR, exist_ok=True)

# Create storage directory for Render
STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(APP_DIR, "storage"))
os.makedirs(STORAGE_DIR, exist_ok=True)
if os.path.isdir(HLS_DIR):
    app.mount("/hls", StaticFiles(directory=HLS_DIR), name="hls")

# Mount final HLS directory (created after finalize step)
FINAL_HLS_DIR = os.path.join(OUTPUTS_DIR, "final_hls")
os.makedirs(FINAL_HLS_DIR, exist_ok=True)
app.mount("/hls_final", StaticFiles(directory=FINAL_HLS_DIR), name="hls_final")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def ensure_dirs() -> None:
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(STREAM_DIR, exist_ok=True)


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)) -> dict:
    """Accept a multipart video file and store it under input/"""
    ensure_dirs()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")
    base_name = os.path.basename(file.filename)
    name, ext = os.path.splitext(base_name)
    unique_name = f"{name}_{uuid4().hex[:8]}{ext or ''}"
    dest_path = os.path.join(INPUT_DIR, unique_name)
    try:
        with open(dest_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        await file.close()
    return {"filename": unique_name, "path": dest_path}


def iter_file_range(path: str, start: int, end: int, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            yield data
            remaining -= len(data)


range_re = re.compile(r"bytes=(\d+)-(\d*)")


@app.get("/stream")
def stream_file(filename: str = Query(..., description="Filename in input/ or output/")):
    """HTTP range streaming for a local file.
    Priority search in output/ then input/.
    """
    # Backward-compat: accept old name without underscore
    base = os.path.basename(filename)
    if base == "final_output_vr180.mp4":
        base = "final_output_vr_180.mp4"
    outputs_path = os.path.join(OUTPUTS_DIR, base)
    input_path = os.path.join(INPUT_DIR, base)
    path = outputs_path if os.path.exists(outputs_path) else input_path
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(path)
    content_type = "video/mp4" if path.lower().endswith(".mp4") else "application/octet-stream"

    # Manually parse Range header from the ASGI scope via dependency injection
    # FastAPI exposes headers on the request object; we can access it via request in a dependency
    from fastapi import Request

    async def _range_response(request: Request):
        range_header = request.headers.get("range")
        if range_header is None:
            return FileResponse(path, media_type=content_type)

        match = range_re.match(range_header)
        if not match:
            return Response(status_code=416)
        start = int(match.group(1))
        end = match.group(2)
        end = int(end) if end else file_size - 1
        if start >= file_size or end >= file_size or start > end:
            return Response(status_code=416)

        response = StreamingResponse(
            iter_file_range(path, start, end),
            media_type=content_type,
            status_code=206,
        )
        response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Length"] = str(end - start + 1)
        return response

    return _range_response


@app.get("/hls_refresh")
def hls_refresh() -> dict:
    """Ensure HLS static mount is attached if the directory now exists."""
    global HLS_DIR
    new_dir = _find_hls_dir()
    mounted = any([r.path == "/hls" for r in getattr(app, "routes", [])])
    if os.path.isdir(new_dir) and not mounted:
        app.mount("/hls", StaticFiles(directory=new_dir), name="hls")
        HLS_DIR = new_dir
    # Try mounting final hls as well
    global FINAL_HLS_DIR
    final_dir = os.path.join(OUTPUTS_DIR, "final_hls")
    final_mounted = any([r.path == "/hls_final" for r in getattr(app, "routes", [])])
    if os.path.isdir(final_dir) and not final_mounted:
        app.mount("/hls_final", StaticFiles(directory=final_dir), name="hls_final")
        FINAL_HLS_DIR = final_dir
    return {"mounted": os.path.isdir(new_dir), "final_mounted": os.path.isdir(final_dir), "dir": new_dir, "final_dir": final_dir}


def _ensure_hls_mounted_and_path() -> str:
    """Ensure HLS is mounted and return playlist path if present, else empty string."""
    global HLS_DIR
    new_dir = _find_hls_dir()
    mounted = any([r.path == "/hls" for r in getattr(app, "routes", [])])
    if os.path.isdir(new_dir) and not mounted:
        app.mount("/hls", StaticFiles(directory=new_dir), name="hls")
        HLS_DIR = new_dir
    playlist = os.path.join(HLS_DIR, "output.m3u8") if HLS_DIR else ""
    return playlist if playlist and os.path.exists(playlist) else ""


@app.get("/hls_manifest")
def hls_manifest() -> dict:
    """Return the HLS playlist URL for the frontend if available."""
    playlist_fs = _ensure_hls_mounted_and_path()
    # Prefer final HLS when available
    final_playlist = os.path.join(FINAL_HLS_DIR, "output.m3u8")
    if os.path.exists(final_playlist):
        return {"ready": True, "url": "/hls_final/output.m3u8", "type": "final"}
    # Fall back to incremental HLS
    if not playlist_fs:
        return {"ready": False, "url": None}
    return {"ready": True, "url": "/hls/output.m3u8", "type": "incremental"}


@app.get("/stream_status")
def stream_status(mode: str = Query("vr180", description="Processing mode: vr180 or anaglyph")) -> dict:
    """Report availability of both HLS playlist and final MP4 for the frontend to poll.
    Frontend can call this every ~40 seconds.
    """
    # Ensure dirs and possible HLS mount
    ensure_dirs()
    playlist_fs = _ensure_hls_mounted_and_path()
    hls_exists = bool(playlist_fs)
    
    # Check for appropriate output file based on mode
    if mode == "anaglyph":
        mp4_path = os.path.join(OUTPUTS_DIR, "final_output_anaglyph.mp4")
    else:
        mp4_path = os.path.join(OUTPUTS_DIR, "final_output_vr_180.mp4")
    
    mp4_exists = os.path.exists(mp4_path)
    return {
        "hls": {"exists": hls_exists, "url": "/hls/output.m3u8" if hls_exists else None},
        "mp4": {"exists": mp4_exists, "url": f"/stream?filename={os.path.basename(mp4_path)}" if mp4_exists else None},
        "mode": mode
    }


@app.get("/download")
def download_file(filename: str = Query(..., description="Filename in outputs/ or input/")):
    outputs_path = os.path.join(OUTPUTS_DIR, os.path.basename(filename))
    input_path = os.path.join(INPUT_DIR, os.path.basename(filename))
    path = outputs_path if os.path.exists(outputs_path) else input_path
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "video/mp4" if path.lower().endswith(".mp4") else "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=os.path.basename(path))


@app.get("/proxy")
async def proxy_stream(url: str = Query(..., description="Remote video URL to proxy")):
    """Stream or download a remote resource via proxy with chunked transfer."""
    try:
        client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def _gen():
        async with client.stream("GET", url) as resp:
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail="Upstream error")
            async for chunk in resp.aiter_bytes(chunk_size=1024 * 64):
                if chunk:
                    yield chunk

    headers = {}
    # Best-effort content-type passthrough
    try:
        async with client.head(url) as head_resp:
            ctype = head_resp.headers.get("content-type")
            if ctype:
                headers["Content-Type"] = ctype
    except Exception:
        pass

    return StreamingResponse(_gen(), headers=headers)


@app.post("/process")
async def process_video(
    request: Request,
    background_tasks: BackgroundTasks,
    filename: Optional[str] = Query(None, description="Existing filename under input/"),
    add_audio: bool = Query(True),
):
    """Kick off processing using src.main.main without duplicating logic.
    Accepts either an uploaded file (multipart) or a filename already present in input/.
    Tolerates empty/absent file fields.
    """
    ensure_dirs()

    # Try to read an optional file from multipart form without triggering validation errors
    upload: Optional[UploadFile] = None
    try:
        form = await request.form()
        maybe_file = form.get("file")
        if isinstance(maybe_file, UploadFile) and getattr(maybe_file, "filename", None):
            upload = maybe_file
    except Exception:
        upload = None

    if upload is None and not filename:
        raise HTTPException(status_code=400, detail="Provide either file or filename")

    input_path: Optional[str] = None
    if upload is not None:
        safe_name = os.path.basename(upload.filename)
        input_path = os.path.join(INPUT_DIR, safe_name)
        try:
            # Overwrite if exists
            if os.path.exists(input_path):
                os.remove(input_path)
            with open(input_path, "wb") as f:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Save failed: {e}")
        finally:
            await upload.close()
    else:
        # filename may arrive quoted from some UIs; strip quotes if present
        assert filename is not None
        cleaned = filename.strip('"')
        safe_name = os.path.basename(cleaned)
        candidate = os.path.join(INPUT_DIR, safe_name)
        if not os.path.exists(candidate):
            raise HTTPException(status_code=404, detail="Filename not found under input/")
        input_path = candidate

    # Delegate to pipeline in background
    assert input_path is not None
    background_tasks.add_task(process_main, input_path, add_audio)
    return {"status": "accepted", "input": input_path, "add_audio": add_audio}


@app.post("/process_anaglyph")
async def process_anaglyph_video(
    request: Request,
    background_tasks: BackgroundTasks,
    filename: Optional[str] = Query(None, description="Existing filename under input/"),
    add_audio: bool = Query(True),
):
    """Process video for anaglyph 3D effect.
    Accepts either an uploaded file (multipart) or a filename already present in input/.
    """
    ensure_dirs()

    # Try to read an optional file from multipart form without triggering validation errors
    upload: Optional[UploadFile] = None
    try:
        form = await request.form()
        maybe_file = form.get("file")
        if isinstance(maybe_file, UploadFile) and getattr(maybe_file, "filename", None):
            upload = maybe_file
    except Exception:
        upload = None

    if upload is None and not filename:
        raise HTTPException(status_code=400, detail="Provide either file or filename")

    input_path: Optional[str] = None
    if upload is not None:
        safe_name = os.path.basename(upload.filename)
        input_path = os.path.join(INPUT_DIR, safe_name)
        try:
            # Overwrite if exists
            if os.path.exists(input_path):
                os.remove(input_path)
            with open(input_path, "wb") as f:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Save failed: {e}")
        finally:
            await upload.close()
    else:
        # filename may arrive quoted from some UIs; strip quotes if present
        assert filename is not None
        cleaned = filename.strip('"')
        safe_name = os.path.basename(cleaned)
        candidate = os.path.join(INPUT_DIR, safe_name)
        if not os.path.exists(candidate):
            raise HTTPException(status_code=404, detail="Filename not found under input/")
        input_path = candidate

    # Delegate to anaglyph pipeline in background
    assert input_path is not None
    background_tasks.add_task(main_anaglyph, input_path, add_audio)
    return {"status": "accepted", "input": input_path, "add_audio": add_audio, "mode": "anaglyph"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=os.getenv("RELOAD", "0") == "1")


