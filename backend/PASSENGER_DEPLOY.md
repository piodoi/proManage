# Phusion Passenger Deployment Guide for ProManage Backend

## Prerequisites

1. cPanel/WHM hosting with Phusion Passenger enabled
2. Python 3.11+ available
3. SSH access to the server

## Directory Structure

```
/home/username/
├── promanage/
│   └── backend/
│       ├── passenger_wsgi.py    # Passenger entry point
│       ├── .htaccess            # Apache config
│       ├── .env                 # Environment variables
│       ├── app/                 # FastAPI application
│       ├── tmp/                 # Create this directory
│       │   └── restart.txt      # Touch to restart app
│       └── requirements.txt     # Python dependencies
└── public_html/
    └── api/                     # Symlink or subdomain pointing to backend
```

## Setup Steps

### 1. Upload Files

Upload the entire `backend/` directory to your hosting account.

### 2. Create Python Virtual Environment

```bash
cd ~/promanage/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Or using Poetry:
```bash
cd ~/promanage/backend
pip install poetry
poetry install --no-dev
```

### 3. Create tmp Directory

```bash
mkdir -p ~/promanage/backend/tmp
```

### 4. Configure .htaccess

Edit `.htaccess` and update:
- `PassengerPython` - path to your virtualenv Python
- `PassengerAppRoot` - path to your backend directory

Example:
```apache
PassengerPython /home/yourusername/promanage/backend/venv/bin/python
PassengerAppRoot /home/yourusername/promanage/backend
```

### 5. Configure Environment Variables

Edit `.env` file with production values:
- Set `DATABASE_URL` to your production database
- Update `FRONTEND_URL` and `CORS_ORIGINS`
- Use strong secrets for `JWT_SECRET` and `ENCRYPTION_KEY`

### 6. Setup via cPanel (Alternative)

If using cPanel's "Setup Python App" feature:

1. Go to cPanel → Setup Python App
2. Click "Create Application"
3. Settings:
   - Python version: 3.11
   - Application root: `promanage/backend`
   - Application URL: `api.yourdomain.com` or `/api`
   - Application startup file: `passenger_wsgi.py`
   - Application Entry point: `application`
4. Click "Create"
5. Install dependencies via the cPanel interface or SSH

### 7. Database Setup

For MySQL on shared hosting:
```bash
# Update .env
DATABASE_URL=mysql+pymysql://username_dbuser:password@localhost/username_dbname
```

### 8. Restart Application

After any changes:
```bash
touch ~/promanage/backend/tmp/restart.txt
```

Or via cPanel: Click "Restart" in the Python App interface.

## Troubleshooting

### Check Logs

```bash
# Passenger/Apache error log
tail -f ~/logs/error.log

# Application stdout
tail -f ~/logs/passenger.log
```

### Common Issues

1. **500 Internal Server Error**
   - Check file permissions (755 for directories, 644 for files)
   - Verify Python path in .htaccess
   - Check error logs

2. **Module Not Found**
   - Ensure virtualenv is activated in PassengerPython path
   - Verify all dependencies installed

3. **Database Connection Failed**
   - Check DATABASE_URL in .env
   - Verify database credentials and permissions

4. **CORS Errors**
   - Update CORS_ORIGINS in .env to include your frontend domain

### Test Locally

```bash
cd ~/promanage/backend
source venv/bin/activate
python -c "from passenger_wsgi import application; print('OK')"
```

## Production Checklist

- [ ] Set `DEBUG=0` or remove debug flags
- [ ] Use strong, unique secrets
- [ ] Configure proper CORS origins
- [ ] Set up SSL/HTTPS
- [ ] Configure database backups
- [ ] Set appropriate file permissions
- [ ] Test all API endpoints
