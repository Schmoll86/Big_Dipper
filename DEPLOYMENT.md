# Little Dipper Deployment Guide

## Docker Deployment (Recommended)

### Quick Start

```bash
# Start the bot
docker-compose up -d

# Check logs
docker logs -f little-dipper

# Stop the bot
docker-compose down

# Restart (loads new config)
docker-compose restart
```

## How Code Changes Take Effect

**Python loads all code into memory at startup.**

Changes to `config.py`, `main.py`, or `dip_logic.py` do NOT affect running processes until you restart:

```bash
docker-compose restart
```

## Remote Deployment (Mac Mini Setup)

### One-Time Setup

1. **Enable SSH on Mac Mini:**
   - System Preferences → Sharing → Remote Login → ON
   - Note the hostname (e.g., `mac-mini.local`)

2. **Install Docker on Mac Mini:**
   ```bash
   ssh schmoll@mac-mini.local
   # Install Docker Desktop or via Homebrew
   brew install docker docker-compose
   ```

3. **Clone repo on Mac Mini:**
   ```bash
   ssh schmoll@mac-mini.local
   cd ~/Desktop
   git clone <your-repo-url> Little_Dipper
   cd Little_Dipper
   ```

4. **Set up .env:**
   ```bash
   cp .env.example .env
   # Edit with your Alpaca credentials
   nano .env
   ```

5. **Start the bot:**
   ```bash
   docker-compose up -d
   ```

### Daily Workflow (Edit on MacBook Air, Run on Mac Mini)

```bash
# 1. Make changes on MacBook Air
vim config.py

# 2. Commit and push
git add -A
git commit -m "Update config"
git push

# 3. Deploy to Mac Mini
./deploy.sh
```

The `deploy.sh` script will:
- SSH into Mac Mini
- Pull latest code
- Restart Docker container
- Show you the status

### Manual Deployment

```bash
# SSH into Mac Mini
ssh schmoll@mac-mini.local

# Pull latest code
cd ~/Desktop/Little_Dipper
git pull

# Restart container
docker-compose restart

# Check logs
docker logs -f little-dipper
```

## Monitoring

```bash
# View live logs
docker logs -f little-dipper

# View last 50 lines
docker logs --tail 50 little-dipper

# Check container status
docker ps | grep dipper

# Check resource usage
docker stats little-dipper
```

## Troubleshooting

### Container won't start
```bash
# Check for errors
docker logs little-dipper

# Rebuild image
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Config not updating
1. Verify file saved correctly
2. Ensure you restarted container: `docker-compose restart`
3. Check for Python syntax errors: `python -m py_compile config.py`

### Multiple instances running
```bash
# Should show only ONE container
docker ps -a | grep dipper

# Remove duplicate containers
docker rm -f little-dipper
docker-compose up -d
```

## Important Notes

### Trading Risks
- **NEVER run multiple instances with same API keys**
- Each instance will trade independently
- Could exceed position limits or margin

### Security
- Store API keys in `.env` file (not in code)
- `.env` is in `.gitignore` (never commit keys)
- Keep Docker images updated

### Logs
- Docker logs rotate automatically (see `docker-compose.yml`)
- Max 10MB per file, 3 files retained
- Logs cleared on container restart

## Update Checklist

When deploying changes:

1. [ ] Stop bot (if running): `docker-compose down`
2. [ ] Make code/config changes
3. [ ] Test locally if possible: `python main.py`
4. [ ] Commit to git
5. [ ] Push to remote
6. [ ] Deploy to Mac Mini: `./deploy.sh`
7. [ ] Verify new config loaded (check logs)
8. [ ] Monitor first few trades
