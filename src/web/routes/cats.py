"""Cat management API routes — full CRUD with live registry refresh."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request

from src.web.dependencies import get_cat_registry
from src.models.types import CatConfig, ContextBudget
from src.providers import create_provider

router = APIRouter(prefix="/cats", tags=["cats"])


def _cat_to_dict(cat_id: str, config: CatConfig, registry) -> Dict:
    """Serialize a CatConfig to API response dict."""
    return {
        "id": cat_id,
        "name": config.name,
        "displayName": config.display_name,
        "provider": config.provider,
        "defaultModel": config.default_model,
        "personality": config.personality,
        "avatar": config.avatar,
        "colorPrimary": config.color_primary,
        "colorSecondary": config.color_secondary,
        "mentionPatterns": config.mention_patterns,
        "cliCommand": config.cli_command,
        "cliArgs": config.cli_args,
        "isAvailable": registry.is_available(cat_id),
        "roles": registry.get_roles(cat_id),
        "evaluation": registry.get_evaluation(cat_id),
    }


def _refresh_agent_registry(request: Request, cat_id: str, config: CatConfig) -> None:
    """Try to create/update provider for a cat in the agent registry."""
    agent_reg = getattr(request.app.state, "agent_registry", None)
    if not agent_reg:
        return
    try:
        provider = create_provider(config)
        # Remove old if exists (safe)
        if cat_id in agent_reg._services:
            del agent_reg._services[cat_id]
        agent_reg.register(cat_id, provider)
    except ValueError:
        pass  # Provider not available, skip


# === READ ===

@router.get("")
async def list_cats(
    request: Request,
    registry=Depends(get_cat_registry),
) -> Dict:
    """List all available cats (from seed config + runtime catalog)."""
    cats = []
    for cat_id in registry.get_all_ids():
        config = registry.try_get(cat_id)
        if config:
            cats.append(_cat_to_dict(cat_id, config, registry))

    return {
        "cats": cats,
        "defaultCat": registry.get_default_id(),
    }


@router.get("/{cat_id}")
async def get_cat(
    cat_id: str,
    registry=Depends(get_cat_registry),
) -> Dict:
    """Get detailed info about a specific cat."""
    config = registry.try_get(cat_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Cat not found: {cat_id}")
    return _cat_to_dict(cat_id, config, registry)


@router.get("/{cat_id}/budget")
async def get_cat_budget(
    cat_id: str,
    registry=Depends(get_cat_registry),
) -> Dict:
    """Get context budget for a cat."""
    config = registry.try_get(cat_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Cat not found: {cat_id}")

    return {
        "catId": cat_id,
        "budget": {
            "maxPromptTokens": config.budget.max_prompt_tokens,
            "maxContextTokens": config.budget.max_context_tokens,
            "maxMessages": config.budget.max_messages,
            "maxContentLengthPerMsg": config.budget.max_content_length_per_msg,
        },
    }


# === INVOKE (placeholder) ===

@router.post("/{cat_id}/invoke")
async def invoke_cat(
    cat_id: str,
    request: Request,
    registry=Depends(get_cat_registry),
) -> Dict:
    """Invoke a cat (placeholder - actual invocation via queue)."""
    config = registry.try_get(cat_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Cat not found: {cat_id}")
    if not registry.is_available(cat_id):
        raise HTTPException(status_code=400, detail=f"Cat {cat_id} is not available")
    return {"success": True, "catId": cat_id, "message": f"Invoked {config.display_name}"}


# === CREATE ===

@router.post("")
async def create_cat(
    request: Request,
    registry=Depends(get_cat_registry),
) -> Dict:
    """Create a new cat (stored in runtime catalog + live registry)."""
    body = await request.json()

    cat_id = body.get("id", "").strip()
    name = body.get("name", "").strip()
    provider = body.get("provider", "").strip()

    if not cat_id:
        raise HTTPException(status_code=400, detail="id is required")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not provider:
        raise HTTPException(status_code=400, detail="provider is required")
    if registry.has(cat_id):
        raise HTTPException(status_code=409, detail=f"Cat '{cat_id}' already exists")

    # Validate mention uniqueness
    mentions = body.get("mentionPatterns", [])
    for mention in mentions:
        existing = registry.get_by_mention(mention)
        if existing:
            raise HTTPException(status_code=409, detail=f"Mention '{mention}' already used by '{existing.cat_id}'")

    # Persist to runtime catalog
    from src.config.runtime_catalog import get_runtime_catalog
    catalog = get_runtime_catalog()
    try:
        catalog.create_cat(
            cat_id=cat_id,
            name=name,
            provider=provider,
            mention_patterns=mentions,
            default_model=body.get("defaultModel"),
            personality=body.get("personality"),
            displayName=body.get("displayName", name),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Register in live CatRegistry
    config = CatConfig(
        cat_id=cat_id,
        breed_id=cat_id,
        name=body.get("displayName", name),
        display_name=body.get("displayName", name),
        provider=provider,
        default_model=body.get("defaultModel", ""),
        personality=body.get("personality", ""),
        mention_patterns=mentions,
        budget=ContextBudget(),
    )
    registry._cats[cat_id] = config
    for pattern in mentions:
        registry._mention_index[pattern.lower().lstrip("@")] = cat_id
        registry._mention_index[pattern.lower()] = cat_id

    # Try to create provider
    _refresh_agent_registry(request, cat_id, config)

    return _cat_to_dict(cat_id, config, registry)


# === UPDATE ===

@router.patch("/{cat_id}")
async def update_cat(
    cat_id: str,
    request: Request,
    registry=Depends(get_cat_registry),
) -> Dict:
    """Update an existing cat's configuration."""
    config = registry.try_get(cat_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Cat not found: {cat_id}")

    body = await request.json()

    # Validate mention uniqueness if changing
    new_mentions = body.get("mentionPatterns")
    if new_mentions is not None:
        for mention in new_mentions:
            existing = registry.get_by_mention(mention)
            if existing and existing.cat_id != cat_id:
                raise HTTPException(status_code=409, detail=f"Mention '{mention}' already used by '{existing.cat_id}'")

    # Update runtime catalog
    from src.config.runtime_catalog import get_runtime_catalog
    catalog = get_runtime_catalog()

    if catalog.get(cat_id):
        # Cat exists in catalog — update it
        update_kwargs = {}
        if body.get("name"):
            update_kwargs["name"] = body["name"]
        if body.get("provider"):
            update_kwargs["provider"] = body["provider"]
        if body.get("defaultModel"):
            update_kwargs["default_model"] = body["defaultModel"]
        if body.get("personality"):
            update_kwargs["personality"] = body["personality"]
        if body.get("displayName"):
            update_kwargs["displayName"] = body["displayName"]
        if new_mentions is not None:
            update_kwargs["mention_patterns"] = new_mentions
        if update_kwargs:
            catalog.update_cat(cat_id, **update_kwargs)
    else:
        # Cat is from seed config — create runtime entry to overlay
        catalog.create_cat(
            cat_id=cat_id,
            name=body.get("name", config.name),
            provider=body.get("provider", config.provider),
            mention_patterns=new_mentions or config.mention_patterns,
            default_model=body.get("defaultModel", config.default_model),
            personality=body.get("personality", config.personality),
            displayName=body.get("displayName", config.display_name),
        )

    # Apply updates to live CatConfig
    if body.get("name"):
        config.name = body["name"]
    if body.get("displayName"):
        config.display_name = body["displayName"]
        config.name = body["displayName"]
    if body.get("provider"):
        config.provider = body["provider"]
    if body.get("defaultModel"):
        config.default_model = body["defaultModel"]
    if body.get("personality"):
        config.personality = body["personality"]
    if new_mentions is not None:
        # Clear old mentions
        for p in config.mention_patterns:
            registry._mention_index.pop(p.lower().lstrip("@"), None)
            registry._mention_index.pop(p.lower(), None)
        config.mention_patterns = new_mentions
        for p in new_mentions:
            registry._mention_index[p.lower().lstrip("@")] = cat_id
            registry._mention_index[p.lower()] = cat_id

    # Refresh provider if provider/model changed
    if body.get("provider") or body.get("defaultModel"):
        _refresh_agent_registry(request, cat_id, config)

    return _cat_to_dict(cat_id, config, registry)


# === DELETE ===

@router.delete("/{cat_id}")
async def delete_cat(
    cat_id: str,
    request: Request,
    registry=Depends(get_cat_registry),
) -> Dict:
    """Delete a cat (only runtime cats can be truly deleted; seed cats are protected)."""
    config = registry.try_get(cat_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Cat not found: {cat_id}")

    # Remove from runtime catalog
    from src.config.runtime_catalog import get_runtime_catalog
    catalog = get_runtime_catalog()
    catalog.delete_cat(cat_id)

    # Remove from live CatRegistry
    # Clean mentions
    for p in config.mention_patterns:
        registry._mention_index.pop(p.lower().lstrip("@"), None)
        registry._mention_index.pop(p.lower(), None)
    registry._cats.pop(cat_id, None)

    # Remove from agent registry
    agent_reg = getattr(request.app.state, "agent_registry", None)
    if agent_reg and agent_reg.get(cat_id):
        agent_reg.unregister(cat_id)

    return {"success": True, "deleted": cat_id}
