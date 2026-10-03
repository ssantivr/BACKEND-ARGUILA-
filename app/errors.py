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
