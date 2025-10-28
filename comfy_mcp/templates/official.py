"""Integration with official ComfyUI workflow templates."""

import json
import aiohttp
import asyncio
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from ..dsl import JsonToDslConverter
from .sync_config import get_sync_config


@dataclass
class OfficialTemplate:
    """Official ComfyUI template metadata."""
    
    name: str
    description: str
    category: str
    workflow_json: Dict[str, Any]
    dsl_content: Optional[str] = None
    preview_images: List[str] = None
    source_url: str = ""
    last_updated: str = ""
    

class OfficialTemplateManager:
    """Manages official ComfyUI workflow templates."""
    
    GITHUB_API_BASE = "https://api.github.com/repos/Comfy-Org/workflow_templates"
    TEMPLATES_PATH = "contents/templates"
    CACHE_DIR = Path.cwd() / ".template_cache"
    
    def __init__(self):
        self.converter = JsonToDslConverter()
        self.templates: Dict[str, OfficialTemplate] = {}
        self.config = get_sync_config()
        self.cache_dir = self.config.cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.last_sync_time: Optional[float] = None
        self.sync_stats = {
            "total_attempted": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "conversion_failures": 0
        }
        
    async def fetch_template_list(self) -> List[Dict[str, Any]]:
        """Fetch list of available templates from GitHub API."""
        url = f"{self.GITHUB_API_BASE}/{self.TEMPLATES_PATH}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch templates: {response.status}")
    
    
    async def download_workflow_json(self, download_url: str) -> Dict[str, Any]:
        """Download and parse workflow JSON file."""
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status == 200:
                    content = await response.text()
                    return json.loads(content)
                else:
                    raise Exception(f"Failed to download workflow: {response.status}")
    
    async def sync_official_templates(self) -> Dict[str, OfficialTemplate]:
        """Sync all official templates and convert to DSL."""
        sync_start_time = time.time()
        print("🔄 Syncing official ComfyUI templates...")
        print(f"📋 Config: max_concurrent={self.config.max_concurrent_downloads}, "
              f"timeout={self.config.request_timeout}s, retries={self.config.max_retries}")
        
        # Reset stats
        self.sync_stats = {
            "total_attempted": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "conversion_failures": 0
        }
        
        try:
            # Fetch template list (files in /templates directory)
            template_list = await self.fetch_template_list()
            
            # Filter for .json files only and apply configuration filters
            json_files = []
            for item in template_list:
                if item["type"] == "file" and item["name"].endswith(".json"):
                    file_size = item.get("size", 0)
                    if self.config.should_sync_template(item["name"], file_size):
                        json_files.append(item)
                    else:
                        self.sync_stats["skipped"] += 1
                        print(f"⏭️  Skipped {item['name']} (filtered by config)")
            
            print(f"📊 Found {len(json_files)} templates to sync ({self.sync_stats['skipped']} skipped by filters)")
            
            # Process templates with concurrency control
            semaphore = asyncio.Semaphore(self.config.max_concurrent_downloads)
            tasks = [self._process_template(semaphore, json_file, template_list) for json_file in json_files]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful templates
            synced_templates = {}
            for result in results:
                if isinstance(result, Exception):
                    self.sync_stats["failed"] += 1
                    print(f"❌ Template processing failed: {result}")
                elif result is not None:
                    template_name, template = result
                    synced_templates[template_name] = template
                    self.sync_stats["successful"] += 1
            
            # Cache results
            await self._cache_templates(synced_templates)
            
            self.templates = synced_templates
            self.last_sync_time = sync_start_time
            
            sync_duration = time.time() - sync_start_time
            print(f"🎉 Sync completed in {sync_duration:.1f}s")
            print(f"📊 Stats: {self.sync_stats['successful']} successful, "
                  f"{self.sync_stats['failed']} failed, "
                  f"{self.sync_stats['skipped']} skipped, "
                  f"{self.sync_stats['conversion_failures']} conversion failures")
            
            return synced_templates
            
        except Exception as e:
            print(f"❌ Failed to sync official templates: {e}")
            # Try to load from cache
            cached_templates = await self._load_cached_templates()
            if cached_templates:
                print(f"📁 Loaded {len(cached_templates)} templates from cache")
            return cached_templates
    
    async def _process_template(self, semaphore: asyncio.Semaphore, json_file: dict, template_list: list) -> Optional[tuple]:
        """Process a single template with concurrency control."""
        async with semaphore:
            template_name = json_file["name"].replace(".json", "")
            self.sync_stats["total_attempted"] += 1
            
            try:
                print(f"📥 Processing template: {template_name}")
                
                # Download workflow with retry logic
                workflow_json = None
                for attempt in range(self.config.max_retries):
                    try:
                        workflow_json = await self.download_workflow_json(json_file["download_url"])
                        break
                    except Exception as e:
                        if attempt == self.config.max_retries - 1:
                            raise e
                        print(f"⚠️  Retry {attempt + 1}/{self.config.max_retries} for {template_name}: {e}")
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                
                # Look for corresponding preview images
                preview_images = []
                image_extensions = ['.webp', '.png', '.jpg', '.jpeg']
                for ext in image_extensions:
                    image_files = [f for f in template_list if f["name"].startswith(template_name) and f["name"].endswith(ext)]
                    preview_images.extend([f["download_url"] for f in image_files])
                
                # Convert to DSL
                dsl_content = None
                try:
                    # Import conversion helpers
                    from ..dsl import is_full_workflow_format, full_workflow_to_simplified
                    
                    # Check if it's in full workflow format and convert if needed
                    if is_full_workflow_format(workflow_json):
                        workflow_json = full_workflow_to_simplified(workflow_json)
                    
                    workflow_ast = self.converter.convert(workflow_json)
                    dsl_content = str(workflow_ast)
                except Exception as e:
                    self.sync_stats["conversion_failures"] += 1
                    print(f"⚠️  Failed to convert {template_name} to DSL: {e}")
                    if not self.config.skip_conversion_errors:
                        raise e
                    if not self.config.save_failed_conversions:
                        return None
                
                # Create template object
                template = OfficialTemplate(
                    name=template_name.replace("_", " ").title(),
                    description=f"Official ComfyUI template: {template_name}",
                    category=self._infer_category(template_name),
                    workflow_json=workflow_json,
                    dsl_content=dsl_content,
                    preview_images=preview_images,
                    source_url=f"https://github.com/Comfy-Org/workflow_templates/blob/main/templates/{json_file['name']}",
                    last_updated=json_file.get("updated_at", "")
                )
                
                print(f"✅ Successfully processed {template_name}")
                return template_name, template
                
            except Exception as e:
                print(f"❌ Failed to process {template_name}: {e}")
                raise e
    
    def _infer_category(self, template_name: str) -> str:
        """Infer template category from name."""
        name_lower = template_name.lower()
        
        if any(word in name_lower for word in ['text-to-image', 'text2img', 'dalle', 'ideogram']):
            return "Text-to-Image"
        elif any(word in name_lower for word in ['image-to-image', 'img2img', 'editing']):
            return "Image-to-Image"
        elif any(word in name_lower for word in ['video', 'motion', 'animation']):
            return "Video Generation"
        elif any(word in name_lower for word in ['inpainting', 'inpaint']):
            return "Image Editing"
        elif any(word in name_lower for word in ['chat', 'conversation', 'ai']):
            return "AI Chat"
        elif any(word in name_lower for word in ['audio', 'sound', 'music']):
            return "Audio"
        elif any(word in name_lower for word in ['3d', 'depth']):
            return "3D Generation"
        else:
            return "Miscellaneous"
    
    async def _cache_templates(self, templates: Dict[str, OfficialTemplate]):
        """Cache templates to local storage."""
        cache_file = self.cache_dir / "official_templates.json"
        
        # Backup existing cache if configured
        if self.config.backup_cache and cache_file.exists():
            backup_file = self.cache_dir / f"official_templates_backup_{int(time.time())}.json"
            cache_file.rename(backup_file)
            print(f"📁 Backed up previous cache to {backup_file.name}")
        
        # Convert to serializable format with metadata
        cache_data = {
            "metadata": {
                "last_sync": time.time(),
                "sync_stats": self.sync_stats,
                "template_count": len(templates),
                "config_hash": hash(str(asdict(self.config))),
                "version": "1.0"
            },
            "templates": {
                name: asdict(template) 
                for name, template in templates.items()
            }
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"💾 Cached {len(templates)} templates to {cache_file}")
    
    def get_sync_stats(self) -> dict:
        """Get current sync statistics."""
        return {
            **self.sync_stats,
            "last_sync_time": self.last_sync_time,
            "cache_dir": str(self.cache_dir),
            "template_count": len(self.templates)
        }
    
    async def _load_cached_templates(self) -> Dict[str, OfficialTemplate]:
        """Load templates from cache."""
        cache_file = self.cache_dir / "official_templates.json"
        
        if not cache_file.exists():
            return {}
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check cache metadata if available
            metadata = cache_data.get("metadata", {})
            if metadata:
                cache_age_hours = (time.time() - metadata.get("last_sync", 0)) / 3600
                print(f"📁 Cache age: {cache_age_hours:.1f} hours")
                
                # Check if cache is too old
                if cache_age_hours > self.config.cache_ttl_hours:
                    print(f"⚠️  Cache is older than {self.config.cache_ttl_hours} hours, consider re-syncing")
            
            templates = {}
            template_data_dict = cache_data.get("templates", cache_data)  # Backward compatibility
            for name, template_data in template_data_dict.items():
                if name != "metadata":  # Skip metadata key
                    templates[name] = OfficialTemplate(**template_data)
            
            print(f"📁 Loaded {len(templates)} templates from cache")
            return templates
            
        except Exception as e:
            print(f"⚠️  Failed to load cached templates: {e}")
            return {}
    
    def get_template(self, name: str) -> Optional[OfficialTemplate]:
        """Get a specific official template."""
        return self.templates.get(name)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all official templates with metadata."""
        return [
            {
                "name": name,
                "display_name": template.name,
                "description": template.description,
                "category": template.category,
                "source": "official",
                "preview_images": template.preview_images or [],
                "source_url": template.source_url,
                "has_dsl": template.dsl_content is not None
            }
            for name, template in self.templates.items()
        ]
    
    def search_templates(
        self, 
        query: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search official templates."""
        results = self.list_templates()
        
        if query:
            query_lower = query.lower()
            results = [
                t for t in results 
                if query_lower in t["name"].lower() 
                or query_lower in t["description"].lower()
                or query_lower in t["category"].lower()
            ]
        
        if category:
            results = [
                t for t in results 
                if t["category"].lower() == category.lower()
            ]
        
        return results


# Global instance
official_manager = OfficialTemplateManager()