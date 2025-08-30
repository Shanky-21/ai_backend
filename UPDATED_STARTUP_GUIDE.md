# 🚀 Updated Startup Guide - Business Insights AI

## ✨ What Changed

The system has been **improved** to separate concerns between the web server and job processing:

- **FastAPI Server**: Handles web requests and API endpoints
- **Job Cron System**: Handles background job processing independently
- **Better Reliability**: If one service crashes, the other continues running
- **Easier Debugging**: Separate logs and processes for each service

---

## 🎯 Quick Start Options

### **Option 1: Full System (Recommended)**
```bash
# Start both FastAPI server and job processing
./start_full_system.sh dev

# Or in background mode
./start_full_system.sh bg --interval 10

# Check status
./start_full_system.sh status

# Stop everything
./start_full_system.sh stop
```

### **Option 2: Individual Services**
```bash
# Terminal 1: Start web server only
python start_server.py

# Terminal 2: Start job processing only
./start_job_cron.sh dev --interval 10
```

### **Option 3: Background Services**
```bash
# Start web server in background
nohup python start_server.py > logs/server.log 2>&1 &

# Start job processing in background
./start_job_cron.sh bg --interval 30

# Check what's running
./start_full_system.sh status
```

---

## 🔧 Service Details

### **FastAPI Server**
- **URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **Handles**: File uploads, immediate analysis requests
- **Logs**: Console output or `logs/server.log`

### **Job Cron System**
- **Function**: Processes jobs from `processing_jobs` table
- **Polling**: Every 30 seconds (configurable)
- **Handles**: Background analysis jobs
- **Logs**: `logs/job_cron.log` or console

---

## 📊 System Status Commands

```bash
# Check everything
./start_full_system.sh status

# Check just job processing
./start_job_cron.sh status

# View logs
tail -f logs/server.log      # FastAPI server logs
tail -f logs/job_cron.log    # Job processing logs
```

---

## 🗄️ Database Job Flow

### **How Jobs Get Created**
Jobs can be added to the `processing_jobs` table in several ways:

1. **Via API endpoint** (if you have one)
2. **Direct database insert**
3. **Programmatically** in your code

### **Example: Add Job to Database**
```python
from app.database import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO processing_jobs (file_id, business_description, job_type, status)
            VALUES (%s, %s, %s, 'pending')
        """, (file_id, "Analyze sales data", "analysis"))
```

### **Job Processing Flow**
1. Job added to `processing_jobs` table with status `'pending'`
2. Cron system finds the job and changes status to `'processing'`
3. System fetches file from `files` table using `file_id`
4. AI workflow analyzes the file
5. Results saved to `insights` table
6. Job status updated to `'completed'` or `'failed'`

---

## 🔄 Migration from Old System

### **What's Different**
- **Before**: Job processing started automatically with web server
- **After**: Job processing runs independently
- **Benefits**: Better separation, improved reliability, easier scaling

### **If You Were Using**:
```bash
python start_server.py  # Old way
```

### **Now Use**:
```bash
./start_full_system.sh dev  # New way - starts both services
```

---

## 🛠️ Development Workflow

### **Normal Development**
```bash
# Start everything for development
./start_full_system.sh dev --interval 5

# This opens two terminals:
# 1. FastAPI server with hot reload
# 2. Job cron with 5-second polling
```

### **Testing Job Processing Only**
```bash
# If you just want to test job processing
./start_job_cron.sh dev --interval 5 --max-jobs 10
```

### **Testing Web Server Only**
```bash
# If you just want to test the API
python start_server.py
```

---

## 🚀 Production Deployment

### **Docker Compose Example**
```yaml
version: '3.8'
services:
  web:
    build: .
    command: python start_server.py
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
    
  job-processor:
    build: .
    command: ./start_job_cron.sh docker --interval 30
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
    depends_on:
      - postgres
      
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: business_insights
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
```

### **Systemd Services**
```bash
# Install job processing as systemd service
./start_job_cron.sh prod

# Create systemd service for web server (example)
sudo systemctl enable fastapi-server
sudo systemctl start fastapi-server
```

---

## 🐛 Troubleshooting

### **Common Issues**

#### **"No jobs being processed"**
```bash
# Check if cron is running
./start_job_cron.sh status

# Check for pending jobs in database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM processing_jobs WHERE status = 'pending';"
```

#### **"Web server not responding"**
```bash
# Check if server is running
curl http://localhost:8000/health

# Check server logs
tail -f logs/server.log
```

#### **"Services conflict"**
```bash
# Stop everything and restart
./start_full_system.sh stop
sleep 2
./start_full_system.sh bg
```

### **Reset Everything**
```bash
# Nuclear option - stop all processes
pkill -f "uvicorn"
pkill -f "job_cron"
pkill -f "start_server"

# Clean up PID files
rm -f /tmp/fastapi_server.pid /tmp/job_cron.pid

# Restart
./start_full_system.sh dev
```

---

## 📈 Monitoring

### **Health Checks**
```bash
# Web server health
curl http://localhost:8000/health

# Job processing health
./start_job_cron.sh status

# Full system status
./start_full_system.sh status
```

### **Performance Monitoring**
```bash
# Check resource usage
ps aux | grep -E "(uvicorn|job_cron)"

# Database connections
psql $DATABASE_URL -c "SELECT COUNT(*) FROM pg_stat_activity WHERE application_name LIKE '%job%';"

# Job throughput (last hour)
psql $DATABASE_URL -c "
SELECT 
    DATE_TRUNC('hour', completed_at) as hour,
    COUNT(*) as completed_jobs
FROM processing_jobs 
WHERE completed_at > NOW() - INTERVAL '24 hours'
  AND status = 'completed'
GROUP BY hour 
ORDER BY hour DESC;
"
```

---

## 🎉 Summary

Your system is now **more robust** and **easier to manage**:

✅ **Separated Services**: Web server and job processing run independently  
✅ **Better Reliability**: One service can run without the other  
✅ **Easier Debugging**: Separate logs and processes  
✅ **Flexible Deployment**: Multiple deployment options  
✅ **Production Ready**: Systemd integration and monitoring  

**Start with**: `./start_full_system.sh dev` and you're good to go! 🚀
