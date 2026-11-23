class MemoryError(Exception):
    code: str = "memory_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class MemoryPolicyError(MemoryError):
    code = "memory_policy_violation"


class MemoryLimitError(MemoryError):
    code = "memory_limit_exceeded"