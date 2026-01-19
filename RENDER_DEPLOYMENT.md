# Render Deployment Guide

## Python Version Issue ⚠️

**Problem**: Render may ignore `runtime.txt` and default to Python 3.13, causing pandas compatibility issues.

**Solutions**:
1. Use `requirements-py313.txt` (Python 3.13 compatible)
2. Force Python 3.11 in Render settings
3. Use `requirements-lite.txt` (minimal dependencies)

## Quick Deploy Options

### Option 1: Python 3.13 Compatible (Recommended)
```bash
Build Command: pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements-py313.txt
```

### Option 2: Force Python 3.11
- In Render dashboard → Environment → Add `PYTHON_VERSION=3.11.9`
- Use `requirements.txt`

### Option 3: Lite Version (Fastest)
```bash
Build Command: pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements-lite.txt
```

## Deployment Steps

1. **Connect Repository**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configuration**
   - **Name**: `aadhaar-analytics-dashboard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements-py313.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app --workers 1 --timeout 300 --preload`

3. **Environment Variables**
   - `FLASK_ENV`: `production`
   - `PYTHONUNBUFFERED`: `1`

## If Build Still Fails

### Error: "pandas compilation failed"
**Solution**: Use lite version
```bash
Build Command: pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements-lite.txt
```

### Error: "Geospatial dependencies failed"
**Solution**: The app will automatically fallback to bar charts

### Error: "Memory/timeout issues"
**Solution**: 
- Upgrade to Starter plan ($7/month)
- Reduce workers to 1
- Increase timeout to 300s

## Performance Notes

- **Data Loading**: ~2-5 minutes on first startup
- **Memory Usage**: ~500MB-1GB
- **Recommended Plan**: Starter ($7/month) or higher
- **Cold Start**: ~30-60 seconds

## Troubleshooting

### Check Python Version in Logs
Look for: `==> Using Python version X.X.X`

### Success Messages
```bash
✅ Data processing completed!
🌐 Dashboard is now ready for use!
```

### Test Endpoints
```bash
# Health check
curl https://your-app.onrender.com/api/status

# Overview data
curl https://your-app.onrender.com/api/overview
```

## Manual Configuration

If auto-detection fails:

**Build Command**:
```bash
pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements-py313.txt
```

**Start Command**:
```bash
gunicorn --bind 0.0.0.0:$PORT app:app --workers 1 --timeout 300 --preload
```