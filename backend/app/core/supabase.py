from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Create the Supabase client once and reuse it (like a singleton bean)."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key.get_secret_value(),
    )
