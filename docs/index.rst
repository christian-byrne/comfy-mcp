ComfyUI MCP Server Documentation
==================================

Welcome to the ComfyUI MCP Server documentation! This package provides a Model Context Protocol (MCP) server that enables AI agents to manage ComfyUI workflows using a human-readable Domain Specific Language (DSL).

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   api_reference
   examples
   development

Quick Start
-----------

Installation::

    pip install comfy-mcp

Basic usage::

    from comfy_mcp.mcp.server import mcp
    
    if __name__ == "__main__":
        mcp.run()

Key Features
------------

🔄 **DSL-First Design**
   Agents work entirely in human-readable DSL, with automatic JSON ↔ DSL conversion.

📁 **File Operations**
   Read, write, list, validate, and analyze ComfyUI workflows.

⚡ **Execution Operations**
   Execute workflows on ComfyUI servers with real-time monitoring.

🎨 **DSL Syntax**
   Intuitive workflow syntax with sections, nodes, and connections.

Architecture
------------

The MCP server exposes 8 core tools:

**File Operations:**
   - ``read_workflow`` - Auto-converts JSON to DSL
   - ``write_workflow`` - Saves DSL as JSON/DSL
   - ``list_workflows`` - Discovers workflow files
   - ``validate_workflow`` - DSL syntax validation
   - ``get_workflow_info`` - Workflow analysis

**Execution Operations:**
   - ``execute_workflow`` - Run DSL workflows on ComfyUI
   - ``get_job_status`` - Monitor execution & download images
   - ``list_comfyui_queue`` - View ComfyUI queue status

Example DSL Workflow
--------------------

.. code-block:: dsl

   ## Model Loading

   checkpoint: CheckpointLoaderSimple
     ckpt_name: sd_xl_base_1.0.safetensors

   ## Text Conditioning

   positive: CLIPTextEncode
     text: a beautiful landscape, detailed, photorealistic
     clip: @checkpoint.clip

   negative: CLIPTextEncode
     text: blurry, low quality
     clip: @checkpoint.clip

   ## Generation

   latent: EmptyLatentImage
     width: 1024
     height: 1024

   sampler: KSampler
     model: @checkpoint.model
     positive: @positive.conditioning
     negative: @negative.conditioning
     latent_image: @latent.latent
     seed: 42
     steps: 20

   ## Output

   decode: VAEDecode
     samples: @sampler.latent
     vae: @checkpoint.vae

   save: SaveImage
     images: @decode.image
     filename_prefix: output

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`