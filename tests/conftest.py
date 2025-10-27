"""Pytest configuration and shared fixtures."""

import pytest
import json
from pathlib import Path
from typing import Dict, Any

import comfy_mcp
from comfy_mcp.dsl import DSLParser, DslToJsonConverter, JsonToDslConverter


@pytest.fixture
def sample_dsl() -> str:
    """Sample DSL workflow for testing."""
    return '''## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-pruned-emaonly-fp16.safetensors

## Text Conditioning

positive: CLIPTextEncode
  text: a cat
  clip: @checkpoint.clip

negative: CLIPTextEncode
  text: blurry
  clip: @checkpoint.clip

## Generation

latent: EmptyLatentImage
  width: 512
  height: 512
  batch_size: 1

sampler: KSampler
  seed: 42
  steps: 5
  cfg: 7.0
  sampler_name: euler
  scheduler: normal
  denoise: 1.0
  model: @checkpoint.model
  positive: @positive.conditioning
  negative: @negative.conditioning
  latent_image: @latent.latent

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
  filename_prefix: test
'''


@pytest.fixture
def sample_json() -> Dict[str, Any]:
    """Sample ComfyUI JSON workflow for testing."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
            }
        },
        "2": {
            "class_type": "CLIPTextEncode", 
            "inputs": {
                "text": "a cat",
                "clip": ["1", 1]
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "blurry", 
                "clip": ["1", 1]
            }
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1
            }
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "steps": 5,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0]
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2]
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": "test"
            }
        }
    }


@pytest.fixture
def dsl_parser() -> DSLParser:
    """DSL parser instance."""
    return DSLParser()


@pytest.fixture
def dsl_to_json_converter() -> DslToJsonConverter:
    """DSL to JSON converter instance.""" 
    return DslToJsonConverter()


@pytest.fixture 
def json_to_dsl_converter() -> JsonToDslConverter:
    """JSON to DSL converter instance."""
    return JsonToDslConverter()


@pytest.fixture
def temp_workflow_file(tmp_path: Path, sample_json: Dict[str, Any]) -> Path:
    """Create a temporary workflow JSON file."""
    workflow_file = tmp_path / "test_workflow.json"
    workflow_file.write_text(json.dumps(sample_json, indent=2))
    return workflow_file


@pytest.fixture
def temp_dsl_file(tmp_path: Path, sample_dsl: str) -> Path:
    """Create a temporary DSL file."""
    dsl_file = tmp_path / "test_workflow.dsl"
    dsl_file.write_text(sample_dsl)
    return dsl_file


class MockContext:
    """Mock MCP context for testing."""
    
    def __init__(self):
        self.messages = []
    
    async def info(self, message: str):
        """Mock info method."""
        self.messages.append(("info", message))
    
    async def error(self, message: str):
        """Mock error method."""
        self.messages.append(("error", message))


@pytest.fixture
def mock_context() -> MockContext:
    """Mock MCP context for testing tools."""
    return MockContext()


@pytest.fixture
def comfyui_not_running():
    """Fixture to indicate ComfyUI is not running (for CI/CD)."""
    import httpx
    try:
        response = httpx.get("http://127.0.0.1:8188/queue", timeout=1.0)
        if response.status_code == 200:
            pytest.skip("ComfyUI is running - skipping offline test")
    except (httpx.RequestError, httpx.TimeoutException):
        pass  # ComfyUI not running, test can proceed


@pytest.fixture 
def comfyui_running():
    """Fixture to require ComfyUI is running."""
    import httpx
    try:
        response = httpx.get("http://127.0.0.1:8188/queue", timeout=1.0)
        if response.status_code != 200:
            pytest.skip("ComfyUI not running - skipping integration test")
    except (httpx.RequestError, httpx.TimeoutException):
        pytest.skip("ComfyUI not running - skipping integration test")