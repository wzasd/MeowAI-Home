"""Workflow REST API endpoints"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/workflow", tags=["workflow"])

# Global instances (set during app initialization)
template_factory = None
dag_executor = None


def set_workflow_instances(factory, executor):
    global template_factory, dag_executor
    template_factory = factory
    dag_executor = executor


@router.get("/templates")
async def list_templates():
    """List available workflow templates."""
    templates = [
        {"id": "tdd", "name": "TDD Development", "description": "Test-driven development workflow"},
        {"id": "review", "name": "Code Review", "description": "Multi-stage code review"},
        {"id": "deploy", "name": "Deploy", "description": "Deployment workflow"},
        {"id": "brainstorm", "name": "Brainstorm", "description": "Parallel ideation"},
        {"id": "parallel", "name": "Parallel", "description": "Parallel execution"},
        {"id": "autoplan", "name": "Auto Plan", "description": "LLM auto-planned workflow"},
    ]
    return templates


@router.get("/active")
async def list_active_workflows():
    """List currently active workflows."""
    # TODO: Track active workflows in dag_executor
    return {"workflows": []}
