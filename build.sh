#!/bin/bash

# Build script for Render deployment

echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "Pre-downloading MiDaS models..."
cd backend
python -c "from src.midas_depth import Midas, ModelType; Midas(ModelType.MIDAS_SMALL)"
cd ..

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Build completed successfully!"
