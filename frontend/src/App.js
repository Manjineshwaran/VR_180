import React, { useState, useEffect, useRef } from "react";
import {
  uploadFile,
  startProcessingByFilename,
  getHlsStreamUrl,
  checkFinalAvailable,
  hlsRefresh,
  BASE_URL,
} from "./api";
import VideoPlayer from "./VideoPlaper";
import "./style.css";

function App() {
  const [mode, setMode] = useState("vr180"); // default to VR180 per requirement
  const [file, setFile] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [streamUrl, setStreamUrl] = useState(null);
  const [finalUrl, setFinalUrl] = useState(null);
  const [showFinalPlayer, setShowFinalPlayer] = useState(false);
  const pollRef = useRef(null);

  const handleProcess = async () => {
    if (!file) return alert("Please choose a video file first.");
    try {
      setIsProcessing(true);
      setFinalUrl(null);

      const uploadRes = await uploadFile(file);
      const filename = uploadRes.filename; // now unique per upload
      setUploadedFilename(filename);

      await startProcessingByFilename(filename, true, mode);

      // Start HLS playback once segments appear; we can set the URL immediately
      await hlsRefresh();
      setStreamUrl(getHlsStreamUrl());

      // Poll for final file availability
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        const res = await checkFinalAvailable(mode);
        if (res.final_url) {
          setFinalUrl(res.final_url);
          setIsProcessing(false);
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, 5000);
    } catch (e) {
      console.error(e);
      alert("Processing failed. Please check backend logs.");
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return (
    <div className="card">
      <h2>VR 180 & Anaglyph Processor</h2>

      <div style={{ marginBottom: 12 }}>
        <label style={{ marginRight: 12 }}>
          <input
            type="radio"
            name="mode"
            value="vr180"
            checked={mode === "vr180"}
            onChange={() => setMode("vr180")}
          />
          VR 180 (recommended)
        </label>
        <label>
          <input
            type="radio"
            name="mode"
            value="anaglyph"
            checked={mode === "anaglyph"}
            onChange={() => setMode("anaglyph")}
          />
          Anaglyph 3D
        </label>
      </div>

      <input
        type="file"
        accept="video/mp4,video/*"
        onChange={(e) => setFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
      />

      <button onClick={handleProcess} disabled={!file || isProcessing}>
        {isProcessing ? "Processing..." : "Process"}
      </button>

      {streamUrl && (
        <>
          <div style={{ marginTop: 12, fontSize: 14, color: "#475569" }}>
            {isProcessing ? `Processing ${mode.toUpperCase()} in background. Preview is streaming...` : `${mode.toUpperCase()} preview ready.`}
          </div>
          <VideoPlayer streamUrl={streamUrl} />
        </>
      )}

      {finalUrl && (
        <>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 12 }}>
            <a href={finalUrl} download className="download-btn">Download Final {mode.toUpperCase()} MP4</a>
            <button onClick={() => setShowFinalPlayer((v) => !v)}>
              {showFinalPlayer ? "Hide Final Player" : `Play Final ${mode.toUpperCase()}`}
            </button>
          </div>
          {showFinalPlayer && (
            <div className="video-container">
              <div style={{ marginBottom: 8, fontSize: 14, color: "#475569", textAlign: "center" }}>
                Final {mode.toUpperCase()} Video
              </div>
              {/* Play final HLS from backend */}
              <VideoPlayer streamUrl={`${BASE_URL}/hls_final/output.m3u8`} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default App;
