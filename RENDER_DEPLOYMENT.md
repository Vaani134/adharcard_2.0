# Render Deployment Guide

## Quick Deploy Options

### Option 1: Full Version (with maps)
Use `requirements.txt` - includes geospatial libraries for choropleth maps

### Option 2: Lite Version (if build fails)
Use `requirements-lite.txt` - fallback to bar charts, faster deployment

## Deployment Steps

1. **Connect Repository**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configuration**
   - **Name**: `aadhaar-analytics-dashboard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app --workers 1 --timeout 300 --preload`

3. **Environment Variables**
   - `PYTHON_VERSION`: `3.11.0`
   - `FLASK_ENV`: `production`
   - `PYTHONUNBUFFERED`: `1`

## If Build Fails

### Common Issues & Solutions

1. **Geospatial Dependencies Fail**
   ```bash
   # Change requirements file in Render settings:
   Build Command: pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements-lite.txt
   ```

2. **Memory Issues**
   - Reduce workers to 1
   - Increase timeout to 300s
   - Use `--preload` flag

3. **Build Timeout**
   - Use `--no-cache-dir` flag
   - Upgrade to paid plan for more build time

## Performance Notes

- **Data Loading**: ~2-5 minutes on first startup
- **Memory Usage**: ~500MB-1GB
- **Recommended Plan**: Starter ($7/month) or higher
- **Cold Start**: ~30-60 seconds

## Troubleshooting

### Check Logs
```bash
# In Render dashboard, go to your service → Logs
# Look for these success messages:
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

## Alternative: Manual Deploy

If automatic detection fails, use manual configuration:

- **Build Command**: `pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt`
- **Start Command**: `python app.py`

The app will automatically detect Render environment and use appropriate settings.