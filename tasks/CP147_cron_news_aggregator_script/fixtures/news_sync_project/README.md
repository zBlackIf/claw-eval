# AI News Sync

Automated AI news aggregation pipeline that runs on a cron schedule.

## Setup

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to customize sources, schedule, and output format.

## Running

```bash
# Manual run
python sync_news.py

# Dry run (no API call)
python sync_news.py --dry-run

# Specific sources only
python sync_news.py --sources arxiv,huggingface
```

## Cron Setup

See `crontab.txt` for the cron configuration.
Install with: `crontab crontab.txt`
