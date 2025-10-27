"""Workflow template definitions."""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class WorkflowTemplate:
    """A workflow template with metadata."""
    
    name: str
    description: str
    category: str
    tags: List[str]
    dsl_content: str
    parameters: Optional[Dict[str, str]] = None
    required_models: Optional[List[str]] = None
    difficulty: str = "beginner"  # beginner, intermediate, advanced


# Template definitions
TEMPLATES = {
    "text2img_basic": WorkflowTemplate(
        name="Basic Text-to-Image",
        description="Simple text-to-image generation with basic prompting",
        category="Generation",
        tags=["text2img", "basic", "stable-diffusion"],
        difficulty="beginner",
        required_models=["v1-5-pruned-emaonly-fp16.safetensors"],
        parameters={
            "prompt": "a beautiful landscape",
            "negative_prompt": "blurry, low quality",
            "width": "512",
            "height": "512",
            "steps": "20",
            "cfg": "7.0",
            "seed": "42"
        },
        dsl_content="""## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-pruned-emaonly-fp16.safetensors

## Text Conditioning

positive: CLIPTextEncode
  text: {prompt}
  clip: @checkpoint.clip

negative: CLIPTextEncode
  text: {negative_prompt}
  clip: @checkpoint.clip

## Generation

latent: EmptyLatentImage
  width: {width}
  height: {height}
  batch_size: 1

sampler: KSampler
  model: @checkpoint.model
  positive: @positive.conditioning
  negative: @negative.conditioning
  latent_image: @latent.latent
  seed: {seed}
  steps: {steps}
  cfg: {cfg}
  sampler_name: euler
  scheduler: normal
  denoise: 1.0

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
  filename_prefix: text2img_basic
"""
    ),
    
    "img2img": WorkflowTemplate(
        name="Image-to-Image",
        description="Transform existing images with text prompts",
        category="Generation",
        tags=["img2img", "transformation", "stable-diffusion"],
        difficulty="beginner",
        required_models=["v1-5-pruned-emaonly-fp16.safetensors"],
        parameters={
            "image_path": "input.png",
            "prompt": "oil painting style",
            "negative_prompt": "blurry, low quality",
            "denoise": "0.7",
            "steps": "20",
            "cfg": "7.0",
            "seed": "42"
        },
        dsl_content="""## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-pruned-emaonly-fp16.safetensors

## Input Image

load_image: LoadImage
  image: {image_path}

encode: VAEEncode
  pixels: @load_image.image
  vae: @checkpoint.vae

## Text Conditioning

positive: CLIPTextEncode
  text: {prompt}
  clip: @checkpoint.clip

negative: CLIPTextEncode
  text: {negative_prompt}
  clip: @checkpoint.clip

## Generation

sampler: KSampler
  model: @checkpoint.model
  positive: @positive.conditioning
  negative: @negative.conditioning
  latent_image: @encode.latent
  seed: {seed}
  steps: {steps}
  cfg: {cfg}
  sampler_name: euler
  scheduler: normal
  denoise: {denoise}

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
  filename_prefix: img2img
"""
    ),
    
    "upscaling": WorkflowTemplate(
        name="Image Upscaling",
        description="Upscale images using AI super-resolution",
        category="Enhancement",
        tags=["upscaling", "super-resolution", "enhancement"],
        difficulty="intermediate",
        required_models=["RealESRGAN_x4plus.pth"],
        parameters={
            "image_path": "input.png",
            "upscale_factor": "4"
        },
        dsl_content="""## Input Image

load_image: LoadImage
  image: {image_path}

## Upscaling

upscaler: ImageUpscaleWithModel
  upscale_model: RealESRGAN_x4plus.pth
  image: @load_image.image

## Output

save: SaveImage
  images: @upscaler.image
  filename_prefix: upscaled_{upscale_factor}x
"""
    ),
    
    "inpainting": WorkflowTemplate(
        name="Inpainting",
        description="Fill masked areas of images with AI-generated content",
        category="Editing",
        tags=["inpainting", "editing", "mask", "stable-diffusion"],
        difficulty="intermediate",
        required_models=["v1-5-inpainting.ckpt"],
        parameters={
            "image_path": "input.png",
            "mask_path": "mask.png",
            "prompt": "beautiful garden",
            "negative_prompt": "blurry, artifacts",
            "steps": "20",
            "cfg": "7.0",
            "seed": "42"
        },
        dsl_content="""## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-inpainting.ckpt

## Input and Mask

load_image: LoadImage
  image: {image_path}

load_mask: LoadImageMask
  image: {mask_path}
  channel: alpha

## Text Conditioning

positive: CLIPTextEncode
  text: {prompt}
  clip: @checkpoint.clip

negative: CLIPTextEncode
  text: {negative_prompt}
  clip: @checkpoint.clip

## Encoding

encode: VAEEncodeForInpaint
  pixels: @load_image.image
  vae: @checkpoint.vae
  mask: @load_mask.mask

## Generation

sampler: KSampler
  model: @checkpoint.model
  positive: @positive.conditioning
  negative: @negative.conditioning
  latent_image: @encode.latent
  seed: {seed}
  steps: {steps}
  cfg: {cfg}
  sampler_name: euler
  scheduler: normal
  denoise: 1.0

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
  filename_prefix: inpainted
"""
    ),
    
    "controlnet_pose": WorkflowTemplate(
        name="ControlNet Pose Control",
        description="Generate images following pose guidance from reference image",
        category="Controlled Generation",
        tags=["controlnet", "pose", "guided-generation"],
        difficulty="advanced",
        required_models=["v1-5-pruned-emaonly-fp16.safetensors", "control_v11p_sd15_openpose.pth"],
        parameters={
            "pose_image": "pose_reference.png",
            "prompt": "professional dancer in elegant attire",
            "negative_prompt": "blurry, deformed, low quality",
            "width": "512",
            "height": "512",
            "steps": "20",
            "cfg": "7.0",
            "seed": "42",
            "control_strength": "1.0"
        },
        dsl_content="""## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-pruned-emaonly-fp16.safetensors

controlnet: ControlNetLoader
  control_net_name: control_v11p_sd15_openpose.pth

## Control Input

control_image: LoadImage
  image: {pose_image}

## Text Conditioning

positive: CLIPTextEncode
  text: {prompt}
  clip: @checkpoint.clip

negative: CLIPTextEncode
  text: {negative_prompt}
  clip: @checkpoint.clip

## ControlNet Application

control_apply: ControlNetApply
  conditioning: @positive.conditioning
  control_net: @controlnet.control_net
  image: @control_image.image
  strength: {control_strength}

## Generation

latent: EmptyLatentImage
  width: {width}
  height: {height}
  batch_size: 1

sampler: KSampler
  model: @checkpoint.model
  positive: @control_apply.conditioning
  negative: @negative.conditioning
  latent_image: @latent.latent
  seed: {seed}
  steps: {steps}
  cfg: {cfg}
  sampler_name: euler
  scheduler: normal
  denoise: 1.0

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
  filename_prefix: controlnet_pose
"""
    ),
    
    "batch_processing": WorkflowTemplate(
        name="Batch Image Processing",
        description="Process multiple images with the same workflow",
        category="Batch Operations",
        tags=["batch", "automation", "processing"],
        difficulty="intermediate",
        required_models=["v1-5-pruned-emaonly-fp16.safetensors"],
        parameters={
            "input_directory": "input_images/",
            "prompt": "enhanced and improved",
            "negative_prompt": "blurry, artifacts",
            "steps": "15",
            "cfg": "7.0",
            "denoise": "0.5"
        },
        dsl_content="""## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-pruned-emaonly-fp16.safetensors

## Batch Input

batch_loader: LoadImageBatch
  mode: incremental
  index: 0
  label: batch_input
  path: {input_directory}
  pattern: *

## Text Conditioning

positive: CLIPTextEncode
  text: {prompt}
  clip: @checkpoint.clip

negative: CLIPTextEncode
  text: {negative_prompt}
  clip: @checkpoint.clip

## Encoding

encode: VAEEncode
  pixels: @batch_loader.image
  vae: @checkpoint.vae

## Generation

sampler: KSampler
  model: @checkpoint.model
  positive: @positive.conditioning
  negative: @negative.conditioning
  latent_image: @encode.latent
  seed: 42
  steps: {steps}
  cfg: {cfg}
  sampler_name: euler
  scheduler: normal
  denoise: {denoise}

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
  filename_prefix: batch_processed
"""
    ),
    
    "style_transfer": WorkflowTemplate(
        name="Style Transfer",
        description="Apply artistic style from one image to another",
        category="Artistic",
        tags=["style-transfer", "artistic", "neural-style"],
        difficulty="advanced",
        required_models=["v1-5-pruned-emaonly-fp16.safetensors"],
        parameters={
            "content_image": "content.png",
            "style_image": "style.png",
            "style_strength": "0.8",
            "steps": "25",
            "cfg": "7.5",
            "seed": "42"
        },
        dsl_content="""## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-pruned-emaonly-fp16.safetensors

## Input Images

content: LoadImage
  image: {content_image}

style: LoadImage
  image: {style_image}

## Style Analysis

style_model: StyleModelLoader
  style_model_name: style_transfer_model.safetensors

style_transfer: StyleModelApply
  conditioning: @positive.conditioning
  style_model: @style_model.style_model
  clip_vision_output: @style.image

## Content Encoding

encode: VAEEncode
  pixels: @content.image
  vae: @checkpoint.vae

## Text Conditioning

positive: CLIPTextEncode
  text: apply artistic style
  clip: @checkpoint.clip

negative: CLIPTextEncode
  text: blurry, artifacts, low quality
  clip: @checkpoint.clip

## Generation

sampler: KSampler
  model: @checkpoint.model
  positive: @style_transfer.conditioning
  negative: @negative.conditioning
  latent_image: @encode.latent
  seed: {seed}
  steps: {steps}
  cfg: {cfg}
  sampler_name: euler
  scheduler: normal
  denoise: {style_strength}

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
  filename_prefix: style_transfer
"""
    ),
}


def get_template_by_name(name: str) -> Optional[WorkflowTemplate]:
    """Get a template by name."""
    return TEMPLATES.get(name)


def get_templates_by_category(category: str) -> List[WorkflowTemplate]:
    """Get all templates in a category."""
    return [t for t in TEMPLATES.values() if t.category == category]


def get_templates_by_tag(tag: str) -> List[WorkflowTemplate]:
    """Get all templates with a specific tag."""
    return [t for t in TEMPLATES.values() if tag in t.tags]


def get_templates_by_difficulty(difficulty: str) -> List[WorkflowTemplate]:
    """Get all templates of a specific difficulty level."""
    return [t for t in TEMPLATES.values() if t.difficulty == difficulty]


def list_all_categories() -> List[str]:
    """Get all unique categories."""
    return list(set(t.category for t in TEMPLATES.values()))


def list_all_tags() -> List[str]:
    """Get all unique tags."""
    tags = set()
    for template in TEMPLATES.values():
        tags.update(template.tags)
    return sorted(list(tags))