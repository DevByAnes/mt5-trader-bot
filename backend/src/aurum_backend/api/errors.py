class ApiFault(Exception):
    def __init__(
        self, code: str, message: str, status: int = 422, field: str | None = None
    ) -> None:
        self.code = code
        self.message = message
        self.status = status
        self.field = field
        super().__init__(message)
