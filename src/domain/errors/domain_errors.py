class DomainError(Exception):
    pass


class ValidationError(DomainError):
    pass


class PathTraversalError(DomainError):
    pass


class LimitsExceededError(DomainError):
    pass


class McpBusinessError(DomainError):
    pass


class TransientError(DomainError):
    pass
