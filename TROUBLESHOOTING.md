# OKC Basketball Data Project - Troubleshooting Guide

## Backend Issues

### Django Setup Problems

**Issue**: `ModuleNotFoundError: No module named 'django'`
```bash
# Solution: Install dependencies
pip install -r backend/requirements.txt
```

**Issue**: `ImportError: Couldn't import Django`
```bash
# Solution: Activate virtual environment
pyenv activate okc
# Or create new venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

**Issue**: `python manage.py runserver` fails
```bash
# Check Django installation
python -m django --version
# Install missing dependencies
pip install -r backend/requirements.txt
```

### Database Connection Issues

**Issue**: `psycopg2.OperationalError: connection to server at "localhost" failed`
```bash
# Solution 1: Start PostgreSQL service
# Windows: Start PostgreSQL service in Services
# Linux/Mac: brew services start postgresql

# Solution 2: Check connection
psql -h localhost -U okcapplicant -d okc
```

**Issue**: `relation "app.events" does not exist`
```bash
# Solution: Run migrations
cd backend
python manage.py makemigrations
python manage.py migrate
```

### ETL Script Issues

**Issue**: `./dev.sh: Permission denied`
```bash
# Solution: Make executable
chmod +x backend/scripts/dev.sh
# Windows: Use dev.bat or dev.ps1 instead
```

**Issue**: ETL script fails with import errors
```bash
# Solution: Set environment variables
export DJANGO_SETTINGS_MODULE=app.settings
export PYTHONPATH=$(pwd)/backend
cd backend/scripts
python load_data.py --dry-run
```

## Frontend Issues

### Angular Setup Problems

**Issue**: `npm install` fails with dependency conflicts
```bash
# Solution: Force install
cd frontend
npm install --force
```

**Issue**: `ng serve` fails with version conflicts
```bash
# Solution: Use correct Angular CLI version
npm install -g @angular/cli@12.1.0 typescript@4.6.4 --force
```

**Issue**: `Module not found` errors in Angular
```bash
# Solution: Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install --force
```

### Build Issues

**Issue**: TypeScript compilation errors
```bash
# Solution: Check TypeScript version
npm list typescript
# Install correct version
npm install typescript@4.6.4 --save-dev
```

**Issue**: Angular Material import errors
```bash
# Solution: Install Angular Material
npm install @angular/material @angular/cdk
```

## Railway Deployment Issues

### CLI Problems

**Issue**: `railway: command not found`
```bash
# Solution 1: Use npx
npx @railway/cli login

# Solution 2: Fix PATH
# Add to PATH: C:\Users\[username]\node_global
npm config get prefix
```

**Issue**: Railway login fails
```bash
# Solution: Clear cache and retry
npx @railway/cli logout
npx @railway/cli login
```

### Service Configuration Issues

**Issue**: `Could not find root directory: backend`
```bash
# Solution: Ensure code is pushed to GitHub
git add .
git commit -m "Add backend code"
git push origin main
# Then set Root Directory to "backend" in Railway
```

**Issue**: Build fails with missing dependencies
```bash
# Solution: Check requirements.txt is up to date
# Ensure all dependencies are listed
pip freeze > backend/requirements.txt
```

### Domain and Networking Issues

**Issue**: Backend not accessible from frontend
```bash
# Solution: Update environment.prod.ts
export const environment = {
  production: true,
  BACKEND_PUBLIC_DOMAIN: 'https://your-backend-domain.up.railway.app'
};
```

**Issue**: CORS errors in browser
```bash
# Solution: Configure CORS in Railway environment variables
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.up.railway.app
CSRF_TRUSTED_ORIGINS=https://your-frontend-domain.up.railway.app
```

## Database Issues

### Local Database Setup

**Issue**: `createuser: command not found`
```bash
# Solution: Add PostgreSQL to PATH
# Windows: Add C:\Program Files\PostgreSQL\[version]\bin to PATH
# Linux/Mac: brew install postgresql
```

**Issue**: `database "okc" does not exist`
```bash
# Solution: Create database
createdb okc
psql okc
```

**Issue**: Permission denied for schema
```bash
# Solution: Grant permissions
psql okc
create schema app;
grant all on schema app to okcapplicant;
```

### Railway Database Issues

**Issue**: Cannot connect to Railway database
```bash
# Solution: Check environment variables in Railway
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

**Issue**: Migration fails on Railway
```bash
# Solution: Run migrations in Railway
railway run python manage.py migrate --noinput
```

## CORS Issues

### Development CORS

**Issue**: CORS error in local development
```bash
# Solution: Update settings.py
CORS_ALLOW_ALL_ORIGINS = True  # For development only
```

### Production CORS

**Issue**: CORS error in production
```bash
# Solution: Configure specific origins
CORS_ALLOWED_ORIGINS = ['https://your-frontend-domain.up.railway.app']
```

## Quick Fixes

### Reset Everything
```bash
# Backend reset
cd backend
rm -rf __pycache__ migrations/__pycache__
python manage.py makemigrations
python manage.py migrate

# Frontend reset
cd frontend
rm -rf node_modules dist
npm install --force
npm run build
```

### Railway Reset
```bash
# Delete and recreate services in Railway dashboard
# Reconnect GitHub repository
# Set correct Root Directory
# Deploy again
```

### Database Reset
```bash
# Local reset
psql okc -c "DROP SCHEMA app CASCADE;"
psql okc -c "CREATE SCHEMA app;"
cd backend
python manage.py migrate
```

## Common Error Messages

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `command not found` | Check PATH or use npx |
| `Permission denied` | Use `chmod +x` or Windows equivalent |
| `CORS error` | Update CORS settings in Railway |
| `Database connection failed` | Check PostgreSQL service |
| `Build failed` | Check Root Directory in Railway |

## Getting Help

1. **Check logs**: Railway dashboard → Service → Logs
2. **Verify environment variables**: Railway dashboard → Service → Variables
3. **Test locally first**: Ensure everything works locally before deploying
4. **Check GitHub**: Ensure all code is pushed to the correct branch
5. **Review documentation**: Check DEPLOYMENT_RAILWAY.md for detailed steps

## Emergency Contacts

- **Railway Support**: Railway dashboard → Help
- **Project Documentation**: See README.md and DEPLOYMENT_RAILWAY.md
- **Local Development**: Use `./dev.sh` scripts for common tasks
