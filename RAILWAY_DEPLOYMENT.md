# Railway Deployment Guide for Pacific Hansard

## Quick Deploy Steps

### 1. Install Railway CLI (optional but recommended)
```bash
npm install -g @railway/cli
```

### 2. Login to Railway
```bash
railway login
```

### 3. Create a new project
```bash
railway init
# Choose "Create new project"
# Give it a name like "pacific-hansard"
```

### 4. Deploy
```bash
# From the project directory
railway up

# Or if you want to use GitHub integration:
# 1. Push your code to GitHub
# 2. Connect Railway to your GitHub repo
# 3. Railway will auto-deploy on push
```

### 5. Your URL
After deployment, Railway will provide you with a URL like:
- `https://pacific-hansard.up.railway.app`
- Or you can set a custom subdomain in Railway dashboard

## What Gets Deployed

- PHP/Apache web server
- Solr search engine (embedded)
- SQLite database (instead of MySQL for free tier)
- Python indexing scripts

## Post-Deployment

1. **Add environment variables in Railway dashboard**:
   - `RAILWAY_VOLUME_MOUNT_PATH=/data` (for persistent storage)
   
2. **Set up a volume** (for data persistence):
   - Go to your Railway project dashboard
   - Click on your service
   - Go to Settings → Volumes
   - Create a new volume mounted at `/data`

3. **Index your data**:
   - SSH into your Railway instance or
   - Trigger the indexer manually through Railway dashboard

## Limitations on Free Tier

- $5/month credit (usually enough for low traffic)
- 512MB RAM (we've optimized for this)
- 1GB persistent storage
- Sleeps after 30 min inactivity

## Custom Domain (Optional)

1. Go to Settings → Domains in Railway
2. Add your custom domain
3. Update your DNS records as instructed

## Monitoring

- Check logs: `railway logs`
- View metrics in Railway dashboard
- Set up health checks at `/`