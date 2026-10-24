class ChargeSmartError(Exception):
    status_code = 502

    def __init__(self, message: str, *, warnings: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.warnings = warnings or []


class InvalidLocationError(ChargeSmartError):
    status_code = 400


class ProviderNotConfiguredError(ChargeSmartError):
    status_code = 503


class ProviderUnavailableError(ChargeSmartError):
    status_code = 502


class StationNotFoundError(ChargeSmartError):
    status_code = 404
