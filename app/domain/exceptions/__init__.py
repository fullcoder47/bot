from app.domain.exceptions.auth_exceptions import (
    AccessDeniedError,
    AuthError,
    LanguageSelectionRequiredError,
    UnauthorizedAccessError,
)
from app.domain.exceptions.company_exceptions import (
    CompanyAlreadyExistsError,
    CompanyAdminAssignmentError,
    CompanyError,
    CompanyNameValidationError,
    CompanyNotFoundError,
    InvalidTelegramIdError,
)

__all__ = [
    "AccessDeniedError",
    "AuthError",
    "CompanyAlreadyExistsError",
    "CompanyAdminAssignmentError",
    "CompanyError",
    "CompanyNameValidationError",
    "CompanyNotFoundError",
    "InvalidTelegramIdError",
    "LanguageSelectionRequiredError",
    "UnauthorizedAccessError",
]
