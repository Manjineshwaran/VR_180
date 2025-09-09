# VR 180 Degree (Monorepo)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.88.0-009688)
![React](https://img.shields.io/badge/React-18.2.0-61DAFB)
![OpenCV](https://img.shields.io/badge/OpenCV-4.5%2B-orange)
![FFmpeg](https://img.shields.io/badge/FFmpeg-5.1%2B-007808)
![Open3D](https://img.shields.io/badge/Open3D-0.17.0-FF6F00)
![MiDaS](https://img.shields.io/badge/MiDaS-3.1-00B0D8)
![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933)
![NumPy](https://img.shields.io/badge/NumPy-1.23%2B-013243)


## Project Overview
This project implements a VR 180-degree video processing pipeline that takes input video and processes it to create an immersive 180-degree VR experience. The following images demonstrate the processing pipeline:

### 1. Input Frame
<img src="Images/1frame.png" width="500" alt="Input Frame">
*The original input frame from the video that will be processed for VR conversion.*

### 2. Depth Map Generation
<img src="Images/2depth_midas.png" width="500" alt="Depth Map">
*Depth estimation using MiDaS, showing the depth information of the scene.*

### 3. Left and Right Views
| Left View | Right View |
|-----------|------------|
| ![Left View](Images/3left_frame.png) | ![Right View](Images/3rightframe.png) |
*Stereo pair generated for the VR experience, showing the left and right eye views.*

### 4. Projected Views
| Left Projection | Right Projection |
|-----------------|------------------|
| ![Left Projection](Images/4left_projection.png) | ![Right Projection](Images/4right_projection.png) |
*The projected views after applying the VR transformation to each eye's perspective.*

### 5. Final Stitched Output
<div style="text-align: center;">
    <img src="Images/5stitch.png" width="500" alt="VR180 Stitching Result">
</div>
*The final stitched VR 180-degree output, ready for immersive viewing in VR headsets.*

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Video Processing**: FFmpeg
- **3D Processing**: Open3D
- **Depth Estimation**: MiDaS
- **Image Processing**: OpenCV, NumPy
- **API Documentation**: Swagger UI (auto-generated)

### Frontend
- **Framework**: React
- **State Management**: React Hooks
- **Video Playback**: HLS.js
- **UI Components**: Material-UI
- **HTTP Client**: Axios

## Structure
- backend/ – FastAPI service, processing pipeline
- frontend/ – React app (HLS preview, final download)

## Prerequisites
- Python 3.10+
- FFmpeg in PATH
- Node 18+

## Backend Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup
```bash
cd frontend
npm install
# Windows PowerShell
$env:REACT_APP_BACKEND_URL="http://localhost:8000"
npm start
```

## Usage
1. Open frontend at http://localhost:3000
2. Choose VR180, select a video, click Process
3. Watch live preview via HLS (auto-refreshing)
4. When complete, either:
   - Download final MP4, or
   - Play final HLS at `/hls_final/final.m3u8`

## Notes
- Outputs and temporary data are ignored by git.
- For production, serve frontend behind a reverse proxy to backend `/hls` and `/hls_final`.
## VR_180

