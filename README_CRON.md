# Job Cron Processor

Automated job processing system for Business Insights AI that continuously monitors the `processing_jobs` table and processes pending jobs using the existing AI workflow.

## Quick Start

### 1. Development Mode (Recommended for testing)
```bash
# Run in foreground with debug logging
./start_job_cron.sh dev

# Custom interval (check every 10 seconds)
./start_job_cron.sh dev --interval 10

# Process limited number of jobs
./start_job_cron.sh dev --interval 5 --max-jobs 10
```

### 2. Background Mode (Simple deployment)
```bash
# Start in background
./start_job_cron.sh bg

# Check status
./start_job_cron.sh status

# Stop
./start_job_cron.sh stop
```

### 3. Production Mode (Systemd service)
```bash
# Install and start systemd service
./start_job_cron.sh prod

# Check service status
systemctl status job_cron

# View logs
journalctl -u job_cron -f
```

## How It Works

### Job Processing Flow

1. **Monitor Queue**: Continuously checks `processing_jobs` table for jobs with status `'pending'`
2. **Atomic Selection**: Uses `FOR UPDATE SKIP LOCKED` to safely claim one job at a time
3. **Status Update**: Changes job status from `'pending'` to `'processing'`
4. **File Retrieval**: Gets file paths from `files` table using job's `file_id`
5. **AI Analysis**: Runs the complete AI workflow (`run_complete_workflow`)
6. **Save Results**: Stores insights in `insights` table
7. **Final Status**: Updates job to `'completed'` or `'failed'`

### Key Features

- **One Job at a Time**: Processes jobs sequentially to prevent resource conflicts
- **Atomic Operations**: Uses database locks to prevent race conditions
- **Retry Logic**: Failed jobs are automatically retried up to 3 times
- **Graceful Shutdown**: Handles SIGINT/SIGTERM signals properly
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Configurable**: Adjustable polling intervals and job limits

## Configuration Options

### Command Line Arguments

```bash
python job_cron.py --help
```

- `--interval SECONDS`: Polling interval (default: 30)
- `--max-jobs NUMBER`: Maximum jobs to process before stopping
- `--daemon`: Run as background daemon
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

### Environment Variables

Required:
- `DATABASE_URL` or `POSTGRES_URL`: PostgreSQL connection string

Optional:
- All AI workflow environment variables (OpenAI API keys, etc.)

## Database Schema Requirements

The cron processor expects these tables:

### processing_jobs
```sql
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY,
    file_id UUID REFERENCES files(id),
    job_type VARCHAR(100),
    business_description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

-- Index for efficient job queue queries
CREATE INDEX idx_processing_jobs_status_created 
ON processing_jobs (status, created_at) 
WHERE status = 'pending';
```

### files
```sql
CREATE TABLE files (
    id UUID PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL,
    original_name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### insights
```sql
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES processing_jobs(id),
    insight_type VARCHAR(100),
    content JSONB NOT NULL,
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Deployment Options

### 1. Development
```bash
# Terminal 1: Start the main FastAPI server
python -m app.main

# Terminal 2: Start job processor
./start_job_cron.sh dev --interval 10
```

### 2. Production with Systemd
```bash
# Install service
sudo cp job_cron.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable job_cron
sudo systemctl start job_cron

# Monitor
journalctl -u job_cron -f
```

### 3. Docker
```dockerfile
# Add to your Dockerfile
COPY job_cron.py /app/
COPY start_job_cron.sh /app/
RUN chmod +x /app/start_job_cron.sh /app/job_cron.py

# In docker-compose.yml
services:
  job-processor:
    build: .
    command: ["./start_job_cron.sh", "docker", "--interval", "30"]
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
```

### 4. Multiple Workers
```bash
# Start multiple processors for high throughput
./start_job_cron.sh bg --interval 10 &
./start_job_cron.sh bg --interval 15 &
./start_job_cron.sh bg --interval 20 &

# Each will safely claim different jobs
```

## Monitoring and Debugging

### Check Status
```bash
./start_job_cron.sh status
```

### View Logs
```bash
# Background mode
tail -f logs/job_cron.log

# Systemd service
journalctl -u job_cron -f

# Development mode
# Logs printed to console
```

### Database Queries
```sql
-- Check pending jobs
SELECT COUNT(*) FROM processing_jobs WHERE status = 'pending';

-- Check processing jobs
SELECT id, started_at, business_description 
FROM processing_jobs 
WHERE status = 'processing';

-- Check recent completions
SELECT id, completed_at, error_message
FROM processing_jobs 
WHERE status IN ('completed', 'failed')
ORDER BY completed_at DESC 
LIMIT 10;

-- Check retry counts
SELECT status, retry_count, COUNT(*) 
FROM processing_jobs 
GROUP BY status, retry_count 
ORDER BY status, retry_count;
```

### Performance Metrics
```bash
# Process stats
ps aux | grep job_cron

# Database connections
SELECT COUNT(*) FROM pg_stat_activity WHERE application_name LIKE '%job_cron%';

# Job throughput (last hour)
SELECT 
    DATE_TRUNC('hour', completed_at) as hour,
    COUNT(*) as completed_jobs
FROM processing_jobs 
WHERE completed_at > NOW() - INTERVAL '24 hours'
GROUP BY hour 
ORDER BY hour;
```

## Troubleshooting

### Common Issues

1. **No jobs being processed**
   ```bash
   # Check database connection
   python -c "from app.database import DatabaseManager; db = DatabaseManager(); db.get_connection()"
   
   # Check for pending jobs
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM processing_jobs WHERE status = 'pending';"
   ```

2. **Jobs stuck in 'processing' status**
   ```sql
   -- Reset stuck jobs (older than 1 hour)
   UPDATE processing_jobs 
   SET status = 'pending', started_at = NULL 
   WHERE status = 'processing' 
   AND started_at < NOW() - INTERVAL '1 hour';
   ```

3. **High memory usage**
   ```bash
   # Monitor memory
   ps -o pid,ppid,%mem,%cpu,cmd -p $(pgrep -f job_cron.py)
   
   # Restart if needed
   ./start_job_cron.sh stop
   ./start_job_cron.sh bg --max-jobs 50  # Process in batches
   ```

4. **File not found errors**
   ```sql
   -- Check file paths
   SELECT f.id, f.file_path, f.status 
   FROM files f
   JOIN processing_jobs pj ON pj.file_id = f.id
   WHERE pj.status = 'failed'
   AND pj.error_message LIKE '%file%';
   ```

### Emergency Commands

```bash
# Stop all job processors
pkill -f job_cron.py
sudo systemctl stop job_cron

# Reset all processing jobs to pending
psql $DATABASE_URL -c "UPDATE processing_jobs SET status = 'pending', started_at = NULL WHERE status = 'processing';"

# Clear failed jobs for retry
psql $DATABASE_URL -c "UPDATE processing_jobs SET status = 'pending', retry_count = 0, error_message = NULL WHERE status = 'failed';"
```

## Integration with Existing System

The cron processor integrates seamlessly with your existing FastAPI application:

1. **Same Workflow**: Uses the exact same `run_complete_workflow` function
2. **Same Database**: Shares the same PostgreSQL database and tables  
3. **Same Results**: Produces identical analysis results and insights
4. **Independent**: Runs independently - can start/stop without affecting the API

### Adding Jobs Programmatically

```python
# In your FastAPI endpoints or other code
from app.database import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO processing_jobs (file_id, business_description, job_type)
            VALUES (%s, %s, %s)
        """, (file_id, business_description, "analysis"))
        
# Job will be automatically picked up by the cron processor
```

This system provides a robust, scalable solution for processing analysis jobs in the background while maintaining the same quality and functionality as your interactive API endpoints.
