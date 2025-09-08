# Render Deployment Guide for VR 180 & Anaglyph Processor

## 🚨 Critical Issues for Render Deployment

### **Major Challenges:**
1. **FFmpeg Dependency**: Render doesn't have FFmpeg pre-installed
2. **Memory Requirements**: Needs 4-8GB+ RAM for video processing
3. **Model Downloads**: MiDaS models (~100MB+) downloaded at runtime
4. **File Storage**: Large temporary files need persistent storage
5. **Processing Time**: Video processing may exceed Render's timeout limits

## 📋 Prerequisites

### **Required Render Plan:**
- **Minimum**: Starter Plan ($7/month) - 512MB RAM
- **Recommended**: Standard Plan ($25/month) - 2GB RAM
- **Optimal**: Pro Plan ($85/month) - 8GB RAM

### **Required Services:**
- **Web Service**: For backend API
- **Static Site**: For frontend
- **Persistent Disk**: For file storage (10GB+)

## 🚀 Deployment Steps

### **Step 1: Backend Service**

1. **Create New Web Service**:
   - **Environment**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

2. **Environment Variables**:
   ```
   PYTHONPATH=/opt/render/project/src/backend
   PORT=10000
   STORAGE_DIR=/opt/render/project/src/backend/storage
   ```

3. **Add Persistent Disk**:
   - **Name**: `vr180-storage`
   - **Mount Path**: `/opt/render/project/src/backend/storage`
   - **Size**: 10GB

### **Step 2: Frontend Service**

1. **Create New Static Site**:
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/build`

2. **Environment Variables**:
   ```
   REACT_APP_BACKEND_URL=https://your-backend-service.onrender.com
   ```

### **Step 3: Update Backend for Render**

The backend has been updated with:
- Environment variable support for paths
- Storage directory configuration
- Render-specific port handling

## ⚠️ Known Limitations

### **Render Platform Limitations:**
1. **No FFmpeg**: Must use `ffmpeg-python` (Python wrapper)
2. **Memory Limits**: Starter plan may not handle large videos
3. **Timeout Limits**: Long processing may timeout
4. **No GPU**: CPU-only processing (slower)
5. **Ephemeral Storage**: Files lost on restart (use persistent disk)

### **Workarounds:**
1. **FFmpeg**: Use `ffmpeg-python` package (already included)
2. **Memory**: Upgrade to higher plan or process smaller batches
3. **Timeout**: Use background tasks (already implemented)
4. **Storage**: Use persistent disk for important files
5. **GPU**: Consider AWS/GCP for GPU processing

## 🔧 Configuration Files

### **render.yaml** (Backend):
```yaml
services:
  - type: web
    name: vr180-backend
    env: python
    plan: starter
    buildCommand: |
      pip install -r requirements.txt
      python -c "from src.midas_depth import Midas, ModelType; Midas(ModelType.MIDAS_SMALL)"
    startCommand: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHONPATH
        value: /opt/render/project/src/backend
      - key: PORT
        value: 10000
    disk:
      name: vr180-storage
      mountPath: /opt/render/project/src/backend/storage
      sizeGB: 10
```

### **build.sh**:
```bash
#!/bin/bash
pip install -r backend/requirements.txt
cd backend && python -c "from src.midas_depth import Midas, ModelType; Midas(ModelType.MIDAS_SMALL)"
cd ../frontend && npm install && npm run build
```

## 🐛 Troubleshooting

### **Common Issues:**

1. **FFmpeg Not Found**:
   - Solution: Use `ffmpeg-python` package (already included)

2. **Out of Memory**:
   - Solution: Upgrade to higher plan or reduce batch size

3. **Model Download Fails**:
   - Solution: Pre-download in build command

4. **Files Not Persisting**:
   - Solution: Use persistent disk for storage

5. **CORS Errors**:
   - Solution: Backend already configured for CORS

## 📊 Performance Expectations

### **Starter Plan (512MB RAM)**:
- ✅ Small videos (< 1 minute)
- ❌ Large videos (> 5 minutes)
- ❌ High resolution videos

### **Standard Plan (2GB RAM)**:
- ✅ Medium videos (< 3 minutes)
- ⚠️ Large videos (3-10 minutes)
- ❌ Very high resolution

### **Pro Plan (8GB RAM)**:
- ✅ Large videos (< 30 minutes)
- ✅ High resolution videos
- ⚠️ Very large videos (> 30 minutes)

## 💡 Recommendations

1. **Start with Standard Plan** for testing
2. **Use Pro Plan** for production
3. **Consider AWS/GCP** for heavy processing
4. **Implement video size limits** in frontend
5. **Add progress indicators** for long processing
6. **Use background jobs** for processing

## 🔗 URLs After Deployment

- **Frontend**: `https://your-frontend-service.onrender.com`
- **Backend API**: `https://your-backend-service.onrender.com`
- **Health Check**: `https://your-backend-service.onrender.com/health`
