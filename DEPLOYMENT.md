# Big Dipper Deployment Guide

## Core Principle

**Python loads all code into memory at startup.** Changes to any `.py` file require a restart to take effect.

---

## Docker Deployment (Recommended)

### Quick Start

```bash
# Start
docker-compose up -d

# Check logs
docker logs -f big-dipper

# Stop
docker-compose down

# Restart (loads new config/code)
docker-compose restart
```

### How Restarts Work

- **Config changes** (`config.py`) - Restart required
- **Code changes** (`main.py`, `dip_logic.py`, `utils.py`) - Restart required
- **Environment changes** (`.env`) - Restart required
- **Log rotation** - Happens automatically (see `docker-compose.yml`)

---

## Remote Deployment Pattern

**Scenario:** Edit code on one machine, run on another.

### One-Time Setup (Run Machine)

1. **Enable SSH** (if applicable)
2. **Install Docker**
3. **Clone repository**
4. **Create `.env` file** with Alpaca credentials
5. **Start container:** `docker-compose up -d`

### Daily Workflow

```bash
# 1. Edit code on development machine
vim config.py

# 2. Commit and push to git
git add -A
git commit -m "Update thresholds"
git push

# 3. Deploy to run machine
# Option A: Use deployment script
./deploy.sh

# Option B: Manual SSH
ssh user@run-machine
cd /path/to/Big_Dipper
git pull
docker-compose restart
```

---

## Manual Configuration Changes

**To modify trading parameters:**

1. **Stop Big Dipper:**
   ```bash
   docker-compose down
   # OR
   pkill -f "main.py"
   ```

2. **Edit `config.py`:**
   - Modify SYMBOLS list
   - Adjust DIP_THRESHOLDS
   - Change position sizing
   - Update margin limits
   - Etc.

3. **Validate syntax:**
   ```bash
   python -m py_compile config.py
   ```

4. **Restart Big Dipper:**
   ```bash
   docker-compose up -d
   # OR
   ./start_big_dipper.sh
   ```

5. **Verify changes loaded:**
   ```bash
   # Check startup logs for symbol count, thresholds, etc.
   docker logs big-dipper | head -20
   ```

---

## Monitoring

```bash
# View live logs
docker logs -f big-dipper

# Last N lines
docker logs --tail 50 big-dipper

# Container status
docker ps | grep dipper

# Resource usage
docker stats big-dipper
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check error logs
docker logs big-dipper

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Config Not Taking Effect

**Common causes:**
1. File not saved
2. Forgot to restart
3. Python syntax error

**Fix:**
```bash
# Verify syntax
python -m py_compile config.py

# Force restart
docker-compose restart

# Check logs for errors
docker logs big-dipper | grep -i error
```

### Multiple Instances Running

```bash
# Find all instances
docker ps -a | grep dipper
pgrep -fl "main.py"

# Stop all
docker-compose down
pkill -f "main.py"

# Start fresh
docker-compose up -d
```

---

## Important Warnings

### Trading Risks
- ⚠️ **NEVER run multiple instances with same API keys**
- Each instance trades independently
- Can exceed position limits or margin
- Can cause wash sale violations

### Security
- Store API keys in `.env` file (never in code)
- `.env` is in `.gitignore` (never commit)
- Use Alpaca paper trading first to test
- Keep Docker images updated

### Log Management
- Docker logs rotate automatically (see `docker-compose.yml`)
- Logs persist in volume/file (survives restart)
- Monitor disk space if running long-term

---

## Deployment Checklist

When deploying changes:

1. [ ] Stop bot (if running)
2. [ ] Make code/config changes
3. [ ] Test syntax: `python -m py_compile *.py`
4. [ ] Run unit tests: `python test_dip_logic.py`
5. [ ] Commit to git
6. [ ] Push to remote
7. [ ] Deploy to run machine
8. [ ] Verify changes loaded (check startup logs)
9. [ ] Monitor first cycle for errors

---

## Version Control Strategy

**Best practice:**
- Keep config changes in separate commits
- Use descriptive commit messages
- Tag releases: `git tag v2.17 -m "Add intraday multiplier"`
- Never commit `.env` file

**Example workflow:**
```bash
# Adjust position sizing
vim config.py
git add config.py
git commit -m "Increase base position to 3%"
git push

# Deploy
ssh run-machine "cd /path/to/Big_Dipper && git pull && docker-compose restart"
```

---

## Docker Compose Configuration

**Key settings to understand:**

```yaml
services:
  big-dipper:
    restart: unless-stopped     # Auto-restart on crash
    volumes:
      - ./big_dipper.log:/app/big_dipper.log  # Log persistence
    environment:
      - ALPACA_KEY=${ALPACA_KEY}             # From .env
      - LOG_LEVEL=${LOG_LEVEL:-INFO}         # Default to INFO
```

**Restart policies:**
- `no` - Never restart
- `always` - Always restart (even on reboot)
- `unless-stopped` - Restart unless manually stopped (recommended)
- `on-failure` - Only restart on error

---

## Health Checks

**Add to docker-compose.yml:**
```yaml
healthcheck:
  test: ["CMD", "pgrep", "-f", "main.py"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

**Check health:**
```bash
docker inspect big-dipper | grep Health -A 10
```

---

## Performance Monitoring

```bash
# CPU/Memory usage
docker stats big-dipper

# Disk usage
du -sh big_dipper.log

# Container uptime
docker ps --filter name=big-dipper --format "{{.Status}}"
```

---

## Backup Strategy

**What to backup:**
- `config.py` - Your custom configuration
- `.env` - API credentials (secure location)
- `big_dipper.log` - Trading history
- `web-monitor.db` - Historical data (if using web monitor)

**Backup command:**
```bash
# Create timestamped backup
tar -czf backup-$(date +%Y%m%d).tar.gz config.py .env big_dipper.log
```

---

## Rolling Back Changes

```bash
# View recent commits
git log --oneline -10

# Roll back to previous commit
git checkout <commit-hash> config.py

# Restart with old config
docker-compose restart

# To undo rollback
git checkout main config.py
docker-compose restart
```

---

**Focus:** This guide covers deployment mechanics and operational procedures. Specific configuration values (symbols, thresholds, sizing) are documented in [config.py](config.py) itself.
