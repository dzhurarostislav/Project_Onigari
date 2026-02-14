from contextvars import ContextVar

# Track total tokens consumed in the current execution context
tokens_counter: ContextVar[int] = ContextVar("tokens_counter", default=0)