class AngelOneException(Exception):
    pass

class AngelOneAuthenticationError(AngelOneException):
    pass

class AngelOneNetworkError(AngelOneException):
    pass

class AngelOneRateLimitError(AngelOneException):
    pass

class AngelOneInvalidResponseError(AngelOneException):
    pass
