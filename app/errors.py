class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class AIUnavailableError(Exception):
    pass


class TooManyAttemptsError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class UnsupportedFileError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class InvalidDataError(Exception):
    pass


class NotConfiguredError(Exception):
    pass
