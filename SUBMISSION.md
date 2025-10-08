# OKC Technical Project – Submission

## Basic Information
- **Name**: [Yi Tang]
- **Email**: [manjiji88@gmail.com]
- **Deployed Frontend URL**: [https://frontend-xxxx.up.railway.app]

## Local Development Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver  # http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install --force
npm start  # http://localhost:4200
```

## Data Import & Export

```bash
cd backend/scripts
./dev.sh etl
./dev.sh dump  # Generates backend/scripts/dbexport.psql
```

## Railway Deployment URLs

- **Backend**: [https://backend-xxxx.up.railway.app]
- **Frontend**: [https://frontend-xxxx.up.railway.app]

## Feature Overview

✅ **3NF Database Design** with idempotent ETL pipeline
✅ **Player Summary API** `/api/v1/playerSummary/{playerID}` with sample data structure
✅ **Frontend Dashboard** at `/player-summary` with SVG court visualization
✅ **Coordinate System** with feet units and offensive basket origin
✅ **Railway Deployment** with health checks and CORS configuration

## Known Limitations & Future Improvements

- Database could benefit from additional indexes for complex queries
- Frontend visualization could add more interactive filtering options
- API could support additional player statistics and comparisons
- Real-time data updates could be implemented for live game tracking
- Mobile responsiveness could be enhanced for better user experience