# Template Cache Directory

This directory contains cached official ComfyUI templates synced from the [Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates) repository.

## Files

- `official_templates.json` - Main cache file containing all synced templates with metadata
- `official_templates_backup_*.json` - Backup files from previous syncs

## Automatic Sync

Templates are automatically synchronized via:
- **GitHub Actions** - Daily at 2 AM UTC
- **Manual Trigger** - Via workflow dispatch
- **Code Changes** - When template-related code is modified

## Manual Sync

You can manually sync templates using:

```bash
# Basic sync
python scripts/sync_templates.py sync

# Sync with custom settings
python scripts/sync_templates.py sync --max-concurrent 3 --show-samples

# Check cache info
python scripts/sync_templates.py cache
```

## Cache Format

The cache file contains:
- **metadata** - Sync statistics, timestamps, and configuration
- **templates** - Template data with DSL conversions and preview images

Templates are automatically converted from ComfyUI JSON format to human-readable DSL format for agent use.