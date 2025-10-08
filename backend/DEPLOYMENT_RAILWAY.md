# Railway Deployment Guide

## Overview
This guide covers deploying the basketball data application to Railway platform with proper configuration for production environment.

## Prerequisites
- Railway CLI installed and authenticated
- GitHub repository with backend/frontend code
- Local development environment working
- Database schema and migrations ready

## Environment Variables

### Required Variables
- `DATABASE_URL`: Auto-injected by Railway Postgres (format: `postgresql://user:pass@host:port/db`)
- `DJANGO_SETTINGS_MODULE=app.settings`
- `ALLOWED_HOSTS`: Railway-generated backend domain (e.g., `backend-xxx.up.railway.app`)

### Optional Variables
- `DEBUG=false`: Production mode (recommended)
- `SECURE_SSL_REDIRECT=true`: Force HTTPS redirects
- `CORS_ALLOWED_ORIGINS`: Frontend domain for CORS (e.g., `https://frontend-xxx.up.railway.app`)
- `CSRF_TRUSTED_ORIGINS`: Same as CORS for CSRF protection
- `PGDATABASE`, `PGHOST`, `PGPASSWORD`, `PGPORT`, `PGUSER`: Postgres connection details (auto-injected)

## Deployment Steps

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### 2. Initialize Project
```bash
railway init
```

### 3. Add Database Service
```bash
railway add --database postgres --service database
```

### 4. Add Backend Service with Environment Variables
```bash
railway add \
  --service backend \
  --variables 'DATABASE_URL=${{Postgres.DATABASE_URL}}' \
  --variables 'DJANGO_SETTINGS_MODULE=app.settings' \
  --variables 'DEBUG=false' \
  --variables 'SECURE_SSL_REDIRECT=true'
```

### 5. Configure Backend Service in Railway Dashboard
1. **Connect Repository**: 
   - Go to Railway dashboard
   - Select backend service
   - Click "Source" → "Connect Repo"
   - Select your GitHub repository

2. **Set Root Directory**:
   - In backend service settings
   - Set "Root Directory" to `backend`

3. **Generate Domain**:
   - Go to "Networking" tab
   - Click "Generate Domain"
   - Copy the generated domain (e.g., `backend-xxx.up.railway.app`)

4. **Update Environment Variables**:
   - Add `ALLOWED_HOSTS` with your generated domain
   - Add `CORS_ALLOWED_ORIGINS` with frontend domain (after frontend deployment)

### 6. Build Configuration
Railway will automatically run these commands:
```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

**Note**: Since Root Directory is set to `backend`, commands run from the backend folder.

### 7. Start Configuration
The service will start using the `Procfile`:
```
web: gunicorn app.wsgi:application --bind 0.0.0.0:8080
```

### 8. Deploy and Verify
1. **Deploy**: Click "Deploy" in Railway dashboard
2. **Check Health**: Visit `https://your-backend-domain.up.railway.app/healthz`
   - Should return: `{"ok": true, "service": "basketball-data-api"}`
3. **Test API**: Visit `https://your-backend-domain.up.railway.app/api/v1/playerSummary/1`

### 9. Database Migration (if needed)
If you need to run migrations:
```bash
railway run python manage.py migrate --noinput
```

### 10. Data Import (optional)
To import your local data to Railway database:
```bash
cd backend/scripts
railway connect Postgres
# In psql prompt:
\i dbexport.psql
```

## Frontend Integration

### After Backend Deployment:
1. **Note Backend Domain**: Copy the Railway backend URL (e.g., `https://backend-xxx.up.railway.app`)
2. **Update Frontend Environment**:
   - Edit `frontend/src/environments/environment.prod.ts`
   - Set `BACKEND_PUBLIC_DOMAIN` to your backend Railway URL
   - Example: `BACKEND_PUBLIC_DOMAIN: 'https://backend-xxx.up.railway.app'`

### Deploy Frontend Service:
```bash
railway add --service frontend
```

1. **Configure Frontend Service**:
   - Connect same GitHub repository
   - Set Root Directory to `frontend`
   - Generate domain
   - Set environment variables

2. **Update Backend CORS**:
   - Add frontend domain to `CORS_ALLOWED_ORIGINS` in backend service
   - Add frontend domain to `CSRF_TRUSTED_ORIGINS` in backend service

## Troubleshooting

### Common Issues

1. **Build Fails**:
   - Check Root Directory is set to `backend`
   - Verify `requirements.txt` has all dependencies
   - Check Railway logs for specific errors

2. **Database Connection Errors**:
   - Verify `DATABASE_URL` is set correctly
   - Check if Postgres service is running
   - Ensure schema `app` exists in database

3. **Static Files Not Loading**:
   - Check `STATIC_ROOT` and `STATIC_URL` settings
   - Verify `collectstatic` ran successfully
   - Check WhiteNoise configuration

4. **CORS Errors**:
   - Verify `CORS_ALLOWED_ORIGINS` includes frontend domain
   - Check `ALLOWED_HOSTS` includes backend domain
   - Ensure `CSRF_TRUSTED_ORIGINS` is set

5. **Health Check Fails**:
   - Check if service is running on port 8080
   - Verify Gunicorn configuration
   - Check Railway service logs

### Debugging Commands
```bash
# Check service status
railway status

# View logs
railway logs

# Connect to database
railway connect Postgres

# Run Django commands
railway run python manage.py check
railway run python manage.py shell
```

### Rollback Strategy
If deployment fails:
1. **Delete Service**: In Railway dashboard, delete the backend service
2. **Clean Environment**: Remove any orphaned resources
3. **Recreate**: Follow deployment steps again
4. **Check Configuration**: Verify all environment variables are correct

## Security Considerations

### Production Settings
- Set `DEBUG=false` in production
- Use Railway's built-in HTTPS (automatic)
- Configure proper `ALLOWED_HOSTS`
- Set `CORS_ALLOWED_ORIGINS` to specific frontend domain
- Use `CSRF_TRUSTED_ORIGINS` for CSRF protection

### Monitoring
- Monitor Railway dashboard for service health
- Check logs regularly for errors
- Set up alerts for service downtime
- Monitor database connection health

## Performance Optimization

### Database
- Use Railway's managed Postgres service
- Monitor database performance in Railway dashboard
- Consider connection pooling for high traffic

### Static Files
- WhiteNoise handles static file serving efficiently
- Static files are compressed and cached
- CDN integration available through Railway

### Application
- Gunicorn handles multiple workers automatically
- Monitor memory and CPU usage
- Scale service if needed through Railway dashboard

## Final Verification Checklist

- [ ] Backend service deployed successfully
- [ ] Health endpoint returns 200: `/healthz`
- [ ] API endpoints working: `/api/v1/playerSummary/{id}`
- [ ] Database connected and accessible
- [ ] Static files loading correctly
- [ ] CORS configured for frontend domain
- [ ] Frontend deployed and connected to backend
- [ ] Full application working end-to-end
- [ ] Production security settings enabled
- [ ] Monitoring and logging configured

## Next Steps

1. **Update SUBMISSION.md**: Add frontend public URL for reviewers
2. **Documentation**: Update project README with deployment URLs
3. **Monitoring**: Set up alerts and monitoring
4. **Backup**: Configure database backups
5. **Scaling**: Monitor performance and scale as needed

## Support

- Railway Documentation: https://docs.railway.app/
- Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/
- Gunicorn Configuration: https://docs.gunicorn.org/
- WhiteNoise Configuration: http://whitenoise.evans.io/
