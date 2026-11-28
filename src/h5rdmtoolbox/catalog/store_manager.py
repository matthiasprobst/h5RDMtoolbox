"""Named store registration and selection by storage interface."""

from typing import Dict

from .abstracts import DataStore, MetadataStore, Store


class StoreManager:
    """Store manager that manages the interaction between stores."""

    def __init__(self, stores: Dict[str, Store] = None):
        self._stores: Dict[str, Store] = stores if stores is not None else {}

    def __getattr__(self, item) -> Store:
        """Allows access to stores as attributes."""
        if item in self.stores:
            return self.stores[item]
        return super().__getattribute__(item)

    def __getitem__(self, item):
        """Allows access to stores via indexing."""
        return self.stores[item]

    def __len__(self):
        """Returns the number of stores managed."""
        return len(self.stores)

    def __repr__(self):
        """String representation of the DataStoreManager."""
        store_names = ", ".join(self.stores.keys())
        return f"{self.__class__.__name__}(stores=[{store_names}])"

    def __contains__(self, item) -> bool:
        """Checks if a store exists in the manager."""
        return item in self.stores

    @property
    def stores(self) -> Dict[str, Store]:
        """Returns the stores managed by the manager."""
        return self._stores

    @property
    def data_stores(self) -> Dict[str, DataStore]:
        """Return only stores implementing the data-storage interface."""
        return {k: v for k, v in self.stores.items() if isinstance(v, DataStore)}

    @property
    def metadata_stores(self) -> Dict[str, MetadataStore]:
        """Return only stores implementing the metadata-storage interface."""
        return {k: v for k, v in self.stores.items() if isinstance(v, MetadataStore)}

    def add_store(self, store_name: str, store: Store):
        """Add a new store to the manager."""
        if store_name in self.stores:
            raise ValueError(f"DataStore with name {store_name} already exists.")
        self.stores[store_name] = store
