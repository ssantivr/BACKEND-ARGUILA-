class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class AIUnavailableError(Exception):
    pass


class UnsupportedFileError(Exception):
    pass


class FileTooLargeError(Exception):
    pass
