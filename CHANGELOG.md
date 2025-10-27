# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of ComfyUI MCP Server
- DSL-first workflow management for ComfyUI
- Complete MCP server with 8 tools (file operations + execution)
- Transparent JSON ↔ DSL conversion
- ComfyUI execution integration with real-time monitoring
- Comprehensive test suite with pytest
- CI/CD pipeline with GitHub Actions
- Sphinx documentation with auto-generation
- Code quality tools (Black, Ruff, MyPy, pre-commit)
- CLI interface with `comfy-mcp` command

### Features
- **DSL Parser**: Human-readable workflow syntax
- **File Operations**: read_workflow, write_workflow, list_workflows, validate_workflow, get_workflow_info
- **Execution Operations**: execute_workflow, get_job_status, list_comfyui_queue
- **Real-time Monitoring**: WebSocket integration for execution progress
- **Image Download**: Automatic image retrieval from completed workflows
- **Error Handling**: Comprehensive error messages and validation

## [0.1.0] - 2024-10-26

### Added
- Initial project structure
- Core DSL parsing and conversion functionality
- Basic MCP server implementation
- File operation tools
- Execution tools for ComfyUI integration
- Test infrastructure
- Documentation framework