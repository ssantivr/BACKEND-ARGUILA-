from app.providers.base import ElementDraft, ProviderDataError, SpatialDataProvider
from app.providers.gltf import GltfAdapter
from app.providers.native import NativeJsonAdapter

PROVIDERS: dict[str, SpatialDataProvider] = {
    adapter.name: adapter for adapter in (NativeJsonAdapter(), GltfAdapter())
}

__all__ = ["PROVIDERS", "ElementDraft", "ProviderDataError", "SpatialDataProvider"]
