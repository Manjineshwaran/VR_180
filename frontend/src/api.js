const BASE_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";

export async function uploadFile(file) {
  // Snapshot file to avoid Chrome ERR_UPLOAD_FILE_CHANGED
  let safeFile = file;
  try {
    const buffer = await file.arrayBuffer();
    const blob = new Blob([buffer], { type: file.type || "application/octet-stream" });
    safeFile = new File([blob], file.name, { type: blob.type });
  } catch {}

  const formData = new FormData();
  formData.append("file", safeFile, safeFile.name);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  if (!res.ok) {
    let msg = "Upload failed";
    try { msg = await res.text(); } catch {}
    throw new Error(msg);
  }
  return await res.json(); // { filename, path }
}

export async function startProcessingByFilename(filename, addAudio = true, mode = "vr180") {
  const endpoint = mode === "anaglyph" ? "/process_anaglyph" : "/process";
  const url = new URL(`${BASE_URL}${endpoint}`);
  url.searchParams.set("filename", filename);
  url.searchParams.set("add_audio", String(addAudio));
  const res = await fetch(url.toString(), { method: "POST" });
  if (!res.ok) throw new Error("Process start failed");
  return await res.json();
}

export function getHlsStreamUrl() {
  // Backend serves HLS at /hls when available
  return `${BASE_URL}/hls/output.m3u8`;
}

export async function hlsRefresh() {
  try {
    const res = await fetch(`${BASE_URL}/hls_refresh`);
    if (!res.ok) return { mounted: false };
    return await res.json();
  } catch {
    return { mounted: false };
  }
}

export async function checkFinalAvailable(mode = "vr180") {
  const filename = mode === "anaglyph" ? "final_output_anaglyph.mp4" : "final_output_vr_180.mp4";
  // Use /stream with Range header to cheaply check file existence/readiness
  const streamCheckUrl = new URL(`${BASE_URL}/stream`);
  streamCheckUrl.searchParams.set("filename", filename);
  try {
    const res = await fetch(streamCheckUrl.toString(), {
      method: "GET",
      headers: { Range: "bytes=0-0" },
    });
    if (res.ok) {
      const downloadUrl = new URL(`${BASE_URL}/download`);
      downloadUrl.searchParams.set("filename", filename);
      return { final_url: downloadUrl.toString() };
    }
  } catch (e) {
    // network/CORS issue; treat as not ready yet
  }
  return { final_url: null };
}

export { BASE_URL };
