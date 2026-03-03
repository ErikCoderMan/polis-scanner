from dataclasses import dataclass
from typing import Callable, Awaitable, Dict

@dataclass(slots=True)
class CommandMeta:
    name: str
    handler: Callable[..., Awaitable]
    usage: str
    description: str
    category: str


_COMMANDS: Dict[str, CommandMeta] = {}


def command(*, name: str, usage: str, description: str, category: str):
    def decorator(func: Callable[..., Awaitable]):
        _COMMANDS[name] = CommandMeta(
            name=name,
            handler=func,
            usage=usage,
            description=description,
            category=category,
        )
        return func
    return decorator


def get_commands() -> Dict[str, CommandMeta]:
    return _COMMANDS
