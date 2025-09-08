import React, { useEffect, useRef } from "react";
import Hls from "hls.js";

export default function VideoPlayer({ streamUrl }) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const refreshTimerRef = useRef(null);

  useEffect(() => {
    if (!streamUrl || !videoRef.current) return;

    const videoEl = videoRef.current;
    const makeUrl = () => `${streamUrl}${streamUrl.includes("?") ? "&" : "?"}v=${Date.now()}`;
    const isMp4 = /\.mp4($|\?)/i.test(streamUrl) || streamUrl.includes("/stream?");

    if (isMp4) {
      // Direct MP4 playback
      videoEl.src = makeUrl();
    } else if (videoEl.canPlayType("application/vnd.apple.mpegurl")) {
      videoEl.src = makeUrl();
    } else if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 30,
        liveDurationInfinity: true,
        enableWorker: true,
        lowLatencyMode: false,
        manifestLoadingMaxRetry: 6,
        fragLoadingMaxRetry: 6,
      });
      hls.loadSource(makeUrl());
      hls.attachMedia(videoEl);
      hlsRef.current = hls;

      // Periodically refresh the playlist to avoid browser caching of m3u8 via StaticFiles
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
      refreshTimerRef.current = setInterval(() => {
        try {
          const currentTime = videoEl.currentTime;
          hls.loadSource(makeUrl());
          // restore position shortly after reload to minimize glitch
          setTimeout(() => {
            try { videoEl.currentTime = currentTime; } catch {}
          }, 250);
        } catch {}
      }, 30000);
    }

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
    };
  }, [streamUrl]);

  return (
    <div className="video-container">
      <video ref={videoRef} controls autoPlay style={{ width: "100%", borderRadius: 12 }} />
    </div>
  );
}
