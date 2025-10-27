"""FastAPI HTTP API for DSL conversion."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from .parser import DSLParser
from .converter import (
    DslToJsonConverter,
    JsonToDslConverter,
    is_full_workflow_format,
    full_workflow_to_simplified,
)


app = FastAPI(
    title="ComfyUI DSL API",
    description="Convert between ComfyUI workflows and LLM-optimized DSL",
    version="0.1.0",
)

parser = DSLParser()
dsl_to_json = DslToJsonConverter()
json_to_dsl = JsonToDslConverter()


# Request/Response models
class DslToWorkflowRequest(BaseModel):
    """Request to convert DSL to ComfyUI JSON."""
    dsl: str = Field(..., description="DSL workflow text")


class DslToWorkflowResponse(BaseModel):
    """Response containing ComfyUI JSON workflow."""
    workflow: dict[str, Any] = Field(..., description="ComfyUI JSON workflow")


class WorkflowToDslRequest(BaseModel):
    """Request to convert ComfyUI JSON to DSL."""
    workflow: dict[str, Any] = Field(..., description="ComfyUI JSON workflow")


class WorkflowToDslResponse(BaseModel):
    """Response containing DSL text."""
    dsl: str = Field(..., description="DSL workflow text")


# Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ComfyUI DSL API",
        "version": "0.1.0",
        "endpoints": {
            "dslToWorkflow": "POST /dslToWorkflow - Convert DSL to ComfyUI JSON",
            "workflowToDsl": "POST /workflowToDsl - Convert ComfyUI JSON to DSL",
        },
    }


@app.post("/dslToWorkflow", response_model=DslToWorkflowResponse)
async def dsl_to_workflow(request: DslToWorkflowRequest):
    """Convert DSL to ComfyUI JSON workflow."""
    try:
        # Parse DSL to AST
        workflow_ast = parser.parse(request.dsl)

        # Convert AST to JSON
        json_workflow = dsl_to_json.convert(workflow_ast)

        return DslToWorkflowResponse(workflow=json_workflow)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to convert DSL: {str(e)}")


@app.post("/workflowToDsl", response_model=WorkflowToDslResponse)
async def workflow_to_dsl(request: WorkflowToDslRequest):
    """Convert ComfyUI JSON workflow to DSL.

    Supports both formats:
    - Full ComfyUI format: {"nodes": [...], "links": [...], ...}
    - Simplified API format: {"1": {"class_type": "...", "inputs": {...}}, ...}
    """
    try:
        workflow = request.workflow

        # Auto-detect and convert full format to simplified
        if is_full_workflow_format(workflow):
            workflow = full_workflow_to_simplified(workflow)

        # Convert JSON to AST
        workflow_ast = json_to_dsl.convert(workflow)

        # Convert AST to DSL text
        dsl_text = str(workflow_ast)

        return WorkflowToDslResponse(dsl=dsl_text)

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to convert workflow: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
