"""Storage provider selection (env: STORAGE_PROVIDER=local|supabase)."""
from __future__ import annotations

from app.core.config import get_settings
from app.integrations.storage.local import get_local_provider
from app.integrations.storage.supabase import get_supabase_provider


def get_storage_provider():
    settings = get_settings()
    if settings.storage_provider == "local":
        return get_local_provider()
    return get_supabase_provider()
