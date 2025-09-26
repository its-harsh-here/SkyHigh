# exceptions.py
class UserInputError(ValueError):
    pass

class ExternalAPIError(RuntimeError):
    pass

class ProcessingError(RuntimeError):
    pass
