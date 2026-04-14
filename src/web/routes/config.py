"""Configuration management API routes."""
import os
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from pydantic import BaseModel

from src.config.env_registry import default_env_registry
from src.config.runtime_catalog import get_runtime_catalog, ValidationError


router = APIRouter(prefix="/config", tags=["config"])


class EnvVarUpdate(BaseModel):
    value: str


class CreateCatRequest(BaseModel):
    cat_id: str
    name: str
    provider: str
    mention_patterns: List[str] = []
    default_model: Optional[str] = None
    cli_command: Optional[str] = None
    cli_args: List[str] = []
    personality: Optional[str] = None


class UpdateCatRequest(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    mention_patterns: Optional[List[str]] = None
    default_model: Optional[str] = None
    cli_command: Optional[str] = None
    cli_args: Optional[List[str]] = None
    personality: Optional[str] = None


@router.get("/env")
async def list_env_vars() -> Dict:
    """List all environment variables with metadata."""
    vars_display = default_env_registry.to_dict_for_display()
    return {
        "variables": vars_display,
        "categories": list(default_env_registry.get_categories()),
    }


@router.get("/env/{name}")
async def get_env_var(name: str) -> Dict:
    """Get specific environment variable."""
    var = default_env_registry.get(name)
    if not var:
        raise HTTPException(status_code=404, detail=f"Environment variable not found: {name}")

    current_value = os.environ.get(name, var.default)
    display_value = current_value
    if var.sensitive and current_value:
        display_value = "********"

    return {
        "name": var.name,
        "category": var.category,
        "description": var.description,
        "default": var.default,
        "current": display_value,
        "isSet": name in os.environ,
        "required": var.required,
        "sensitive": var.sensitive,
        "allowedValues": var.allowed_values,
        "example": var.example,
    }


@router.post("/env/{name}")
async def update_env_var(name: str, update: EnvVarUpdate) -> Dict:
    """Update environment variable (runtime only, not persisted)."""
    var = default_env_registry.get(name)
    if not var:
        raise HTTPException(status_code=404, detail=f"Environment variable not found: {name}")

    # Validate allowed values
    if var.allowed_values and update.value not in var.allowed_values:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value. Allowed: {var.allowed_values}"
        )

    # Update in environment (runtime only)
    os.environ[name] = update.value

    return {
        "success": True,
        "name": name,
        "message": "Environment variable updated (runtime only)",
    }


@router.get("/env/export")
async def export_env_vars() -> str:
    """Export environment variables as .env format."""
    return default_env_registry.to_dict_for_export()


@router.get("/runtime-cats")
async def list_runtime_cats() -> Dict:
    """List runtime catalog cats."""
    catalog = get_runtime_catalog()
    cats = catalog.list_all()
    return {
        "cats": cats,
        "catalogPath": str(catalog.path),
        "exists": catalog.exists(),
    }


@router.post("/runtime-cats")
async def create_runtime_cat(request: CreateCatRequest) -> Dict:
    """Create a new runtime cat."""
    catalog = get_runtime_catalog()

    try:
        cat = catalog.create_cat(
            cat_id=request.cat_id,
            name=request.name,
            provider=request.provider,
            mention_patterns=request.mention_patterns,
            default_model=request.default_model,
            cli_command=request.cli_command,
            cli_args=request.cli_args,
            personality=request.personality,
        )
        return {
            "success": True,
            "cat": cat,
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runtime-cats/{cat_id}")
async def get_runtime_cat(cat_id: str) -> Dict:
    """Get a runtime cat."""
    catalog = get_runtime_catalog()
    cat = catalog.get(cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail=f"Cat not found: {cat_id}")
    return cat


@router.patch("/runtime-cats/{cat_id}")
async def update_runtime_cat(cat_id: str, request: UpdateCatRequest) -> Dict:
    """Update a runtime cat."""
    catalog = get_runtime_catalog()

    try:
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        cat = catalog.update_cat(cat_id, **updates)
        return {
            "success": True,
            "cat": cat,
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/runtime-cats/{cat_id}")
async def delete_runtime_cat(cat_id: str) -> Dict:
    """Delete a runtime cat."""
    catalog = get_runtime_catalog()
    catalog.delete_cat(cat_id)
    return {
        "success": True,
        "message": f"Cat {cat_id} deleted",
    }


# ========== Account CRUD ==========


class CreateAccountRequest(BaseModel):
    id: str
    displayName: str
    protocol: str
    authType: str
    baseUrl: Optional[str] = None
    models: Optional[List[str]] = None
    apiKey: Optional[str] = None


class UpdateAccountRequest(BaseModel):
    displayName: Optional[str] = None
    authType: Optional[str] = None
    baseUrl: Optional[str] = None
    models: Optional[List[str]] = None
    apiKey: Optional[str] = None


class TestKeyRequest(BaseModel):
    apiKey: str
    protocol: str
    baseUrl: Optional[str] = None


class BindCatRequest(BaseModel):
    catId: str
    accountRef: str


@router.get("/accounts")
async def list_accounts():
    from src.config.account_store import get_account_store
    store = get_account_store()
    return {"accounts": store.list_accounts()}


@router.post("/accounts")
async def create_account(req: CreateAccountRequest):
    from src.config.account_store import get_account_store
    store = get_account_store()
    try:
        acc = store.create_account(
            id=req.id, displayName=req.displayName, protocol=req.protocol,
            authType=req.authType, baseUrl=req.baseUrl, models=req.models,
            apiKey=req.apiKey,
        )
        return acc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/{account_id}")
async def get_account(account_id: str):
    from src.config.account_store import get_account_store
    store = get_account_store()
    acc = store.get_account(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    return acc


@router.patch("/accounts/{account_id}")
async def update_account(account_id: str, req: UpdateAccountRequest):
    from src.config.account_store import get_account_store
    store = get_account_store()
    try:
        updates = req.model_dump(exclude_unset=True)
        return store.update_account(account_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    from src.config.account_store import get_account_store
    store = get_account_store()
    try:
        store.delete_account(account_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/{account_id}/test-key")
async def test_account_key(account_id: str, req: TestKeyRequest):
    import httpx
    valid = False
    error = None
    try:
        if req.protocol == "anthropic":
            base = req.baseUrl or "https://api.anthropic.com"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{base}/v1/messages",
                    headers={"x-api-key": req.apiKey, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": "claude-sonnet-4-6", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                    timeout=10.0,
                )
                valid = resp.status_code not in (401, 403)
                if not valid:
                    try:
                        error = resp.json().get("error", {}).get("message", "Invalid API key")
                    except Exception:
                        error = f"HTTP {resp.status_code}"
        elif req.protocol == "openai":
            base = req.baseUrl or "https://api.openai.com"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{base}/v1/models",
                    headers={"Authorization": f"Bearer {req.apiKey}"},
                    timeout=10.0,
                )
                valid = resp.status_code == 200
                if not valid:
                    error = "Invalid API key"
        elif req.protocol == "google":
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={req.apiKey}",
                    timeout=10.0,
                )
                valid = resp.status_code == 200
                if not valid:
                    error = "Invalid API key"
        else:
            valid = True
    except Exception as e:
        valid = False
        error = str(e)
    return {"valid": valid, "error": error}


@router.patch("/accounts/bind-cat")
async def bind_cat_to_account(req: BindCatRequest):
    catalog = get_runtime_catalog()
    if not catalog.get(req.catId):
        raise HTTPException(status_code=404, detail=f"Cat '{req.catId}' not found")
    catalog.update_cat(req.catId, accountRef=req.accountRef)
    return {"success": True}
