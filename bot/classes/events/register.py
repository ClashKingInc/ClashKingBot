from typing import Dict, Callable, Any, Type
from event import EventType

registered_logs: Dict[str, tuple[Callable[..., Any], Type]] = {}


def log_event(cls: EventType):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        registered_logs[str(cls)] = (func, cls.owner_class)
        return func

    return decorator
