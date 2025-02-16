from typing import Any, Iterator, TypeVar, Generic

T = TypeVar('T')


class ObjectDictIterable(Generic[T]):
    def __init__(self, items: list[T], key: str):
        """
        Initializes the iterable with a list of objects and a specified key attribute.

        :param items: List of objects.
        :param key: The attribute of the object to use as the dictionary key.
        """
        self._list = items
        self._key = key
        try:
            self._dict = {getattr(item, key): item for item in items}
        except AttributeError as e:
            raise ValueError(f"All items must have the attribute '{key}'") from e

    def __iter__(self) -> Iterator[T]:
        """Allows iteration over the stored objects."""
        return iter(self._list)

    def __getitem__(self, key: Any) -> T:
        """Allows dictionary-style access using the specified attribute as a key."""
        return self._dict[key]

    def __contains__(self, key: Any) -> bool:
        """Allows 'in' checks like a dictionary."""
        return key in self._dict

    def get(self, key: Any, default: Any = None) -> Any:
        """Dictionary-like .get() method with a default value."""
        return self._dict.get(key, default)

    def items(self):
        """Returns dictionary-style items (key-object pairs)."""
        return self._dict.items()

    def keys(self):
        """Returns dictionary-style keys."""
        return self._dict.keys()

    def key_list(self):
        return list(self._dict.keys())

    def values(self):
        """Returns dictionary-style values (the stored objects)."""
        return self._dict.values()

    def __repr__(self):
        return f'ObjectDictIterable({self._list}, key={self._key})'

    def __len__(self) -> int:
        return len(self._list)


