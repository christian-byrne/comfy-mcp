# ComfyUI MCP Server

[![CI](https://github.com/christian-byrne/comfy-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/christian-byrne/comfy-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/christian-byrne/comfy-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/christian-byrne/comfy-mcp)
[![PyPI version](https://badge.fury.io/py/comfy-mcp.svg)](https://badge.fury.io/py/comfy-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DSL-first workflow management for ComfyUI via Model Context Protocol (MCP)**

A production-ready MCP server that enables AI agents to manage ComfyUI workflows using a human-readable Domain Specific Language (DSL). The core design philosophy is **DSL-first**: agents work entirely in DSL format, with JSON conversion happening transparently.

## 🚀 Quick Start

### Installation

```bash
pip install comfy-mcp
```

### Usage with Claude Code

1. Create MCP configuration:
```json
{
  "mcpServers": {
    "comfyui-workflows": {
      "command": "comfy-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

2. Start Claude Code with MCP:
```bash
claude --mcp-config mcp_config.json
```

3. Use in conversation:
```
"Execute this workflow: [paste DSL]"
"List workflows in examples directory"
"Show ComfyUI queue status"
```

## ✨ Features

### 🔄 **DSL-First Design**
- Agents work entirely in human-readable DSL
- Automatic JSON ↔ DSL conversion
- No need to think about format conversion

### 📁 **File Operations**
- `read_workflow` - Auto-converts JSON to DSL
- `write_workflow` - Saves DSL as JSON/DSL  
- `list_workflows` - Discovers workflow files
- `validate_workflow` - DSL syntax validation
- `get_workflow_info` - Workflow analysis

### ⚡ **Execution Operations**
- `execute_workflow` - Run DSL workflows on ComfyUI
- `get_job_status` - Monitor execution & download images
- `list_comfyui_queue` - View ComfyUI queue status

### 🎨 **DSL Syntax Example**

```dsl
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
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   AI Agent      │────│  MCP Server  │────│  ComfyUI    │
│   (Claude)      │    │              │    │   Server    │
└─────────────────┘    └──────────────┘    └─────────────┘
         │                       │                  │
         │ DSL Workflows         │ JSON API         │
         │                       │                  │
         ▼                       ▼                  ▼
   Natural Language ────► DSL Parser ────► JSON Converter
```

**Key Components:**
- **DSL Parser**: Converts human-readable DSL to Abstract Syntax Tree
- **JSON Converter**: Bidirectional conversion between DSL and ComfyUI JSON
- **MCP Server**: Exposes tools via Model Context Protocol
- **Execution Engine**: Integrates with ComfyUI API for workflow execution

## 📖 Documentation

### Core Classes

- **`DSLParser`**: Parse DSL text into Abstract Syntax Tree
- **`DslToJsonConverter`**: Convert DSL AST to ComfyUI JSON
- **`JsonToDslConverter`**: Convert ComfyUI JSON to DSL AST

### MCP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `read_workflow` | Read and convert workflows to DSL | `read_workflow("workflow.json")` |
| `write_workflow` | Write DSL to disk as JSON/DSL | `write_workflow("output.json", dsl)` |
| `list_workflows` | Find workflow files | `list_workflows("./workflows")` |
| `validate_workflow` | Check DSL syntax | `validate_workflow(dsl_content)` |
| `get_workflow_info` | Analyze structure | `get_workflow_info(dsl_content)` |
| `execute_workflow` | Run on ComfyUI | `execute_workflow(dsl_content)` |
| `get_job_status` | Monitor execution | `get_job_status(prompt_id)` |
| `list_comfyui_queue` | View queue | `list_comfyui_queue()` |

## 🛠️ Development

### Setup

```bash
git clone https://github.com/christian-byrne/comfy-mcp.git
cd comfy-mcp
pip install -e ".[dev]"
pre-commit install
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=comfy_mcp --cov-report=html

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Code Quality

```bash
# Format code
black .

# Lint code  
ruff check .

# Type checking
mypy comfy_mcp
```

### Documentation

```bash
cd docs
make html
```

## 🔧 Configuration

### Environment Variables

- `COMFYUI_SERVER`: ComfyUI server address (default: `127.0.0.1:8188`)
- `MCP_DEBUG`: Enable debug logging
- `MCP_LOG_LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR)

### ComfyUI Setup

1. Install ComfyUI
2. Start server: `python main.py --listen 0.0.0.0`
3. Ensure models are installed in `models/checkpoints/`

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests and linting: `pytest && black . && ruff check .`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Amazing stable diffusion GUI
- [FastMCP](https://github.com/jlowin/fastmcp) - Excellent MCP framework  
- [Anthropic](https://www.anthropic.com/) - Model Context Protocol specification

## 📈 Roadmap

- [ ] **v0.2.0**: Enhanced DSL features (templates, macros)
- [ ] **v0.3.0**: Web UI for workflow management
- [ ] **v0.4.0**: Git integration for workflow versioning
- [ ] **v0.5.0**: ComfyUI node discovery and documentation
- [ ] **v1.0.0**: Production deployment features

---

**Built with ❤️ for the ComfyUI and AI automation community**