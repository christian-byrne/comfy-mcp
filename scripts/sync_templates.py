#!/usr/bin/env python3
"""Manual template sync tool for testing and debugging."""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfy_mcp.templates.official import official_manager
from comfy_mcp.templates.sync_config import SyncConfig


async def sync_templates(args):
    """Sync official templates."""
    print(f"🚀 Starting template sync...")
    
    # Configure the manager if needed
    if args.max_concurrent:
        official_manager.config.max_concurrent_downloads = args.max_concurrent
    if args.timeout:
        official_manager.config.request_timeout = args.timeout
    if args.cache_dir:
        official_manager.config.cache_dir = Path(args.cache_dir)
        official_manager.cache_dir = official_manager.config.cache_dir
        official_manager.cache_dir.mkdir(exist_ok=True)
    
    try:
        templates = await official_manager.sync_official_templates()
        
        if not templates:
            print("❌ No templates were synced")
            return 1
        
        print(f"\n✅ Successfully synced {len(templates)} templates")
        
        # Show statistics
        stats = official_manager.get_sync_stats()
        print(f"\n📊 Sync Statistics:")
        for key, value in stats.items():
            if key != "last_sync_time" or value:
                print(f"  {key}: {value}")
        
        # Show sample templates
        if args.show_samples and templates:
            print(f"\n📄 Sample Templates:")
            sample_count = min(3, len(templates))
            for i, (name, template) in enumerate(list(templates.items())[:sample_count]):
                print(f"  {i+1}. {name} ({template.category})")
                print(f"     DSL: {'✅' if template.dsl_content else '❌'}")
                print(f"     Images: {len(template.preview_images or [])}")
        
        # Export templates if requested
        if args.export:
            export_data = {
                "sync_time": stats.get("last_sync_time"),
                "stats": stats,
                "templates": {
                    name: {
                        "name": template.name,
                        "description": template.description,
                        "category": template.category,
                        "has_dsl": template.dsl_content is not None,
                        "preview_count": len(template.preview_images or []),
                        "source_url": template.source_url
                    }
                    for name, template in templates.items()
                }
            }
            
            export_file = Path(args.export)
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            print(f"📁 Exported template data to {export_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def show_cache_info(args):
    """Show information about cached templates."""
    cache_dir = Path(args.cache_dir) if args.cache_dir else official_manager.cache_dir
    cache_file = cache_dir / "official_templates.json"
    
    if not cache_file.exists():
        print(f"❌ No cache file found at {cache_file}")
        return 1
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        metadata = cache_data.get("metadata", {})
        templates = cache_data.get("templates", cache_data)
        
        print(f"📁 Cache File: {cache_file}")
        print(f"📊 Cache Info:")
        print(f"  File size: {cache_file.stat().st_size / 1024:.1f} KB")
        print(f"  Template count: {len([k for k in templates.keys() if k != 'metadata'])}")
        
        if metadata:
            import time
            last_sync = metadata.get("last_sync", 0)
            if last_sync:
                age_hours = (time.time() - last_sync) / 3600
                print(f"  Last sync: {time.ctime(last_sync)} ({age_hours:.1f} hours ago)")
            
            if "sync_stats" in metadata:
                stats = metadata["sync_stats"]
                print(f"  Last sync stats:")
                for key, value in stats.items():
                    print(f"    {key}: {value}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to read cache: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="ComfyUI Template Sync Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync official templates")
    sync_parser.add_argument("--max-concurrent", type=int, help="Maximum concurrent downloads")
    sync_parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    sync_parser.add_argument("--cache-dir", help="Cache directory path")
    sync_parser.add_argument("--show-samples", action="store_true", help="Show sample templates")
    sync_parser.add_argument("--export", help="Export template data to JSON file")
    sync_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # Cache command
    cache_parser = subparsers.add_parser("cache", help="Show cache information")
    cache_parser.add_argument("--cache-dir", help="Cache directory path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "sync":
        return asyncio.run(sync_templates(args))
    elif args.command == "cache":
        return show_cache_info(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())