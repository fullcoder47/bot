class CompanyError(Exception):
    """Base company domain exception."""


class CompanyNameValidationError(CompanyError):
    def __init__(self) -> None:
        super().__init__("Company name is invalid.")


class CompanyAlreadyExistsError(CompanyError):
    def __init__(self, company_name: str) -> None:
        self.company_name = company_name
        super().__init__(f"Company '{company_name}' already exists.")


class CompanyNotFoundError(CompanyError):
    def __init__(self, company_id: int) -> None:
        self.company_id = company_id
        super().__init__(f"Company with id={company_id} was not found.")


class InvalidTelegramIdError(CompanyError):
    def __init__(self) -> None:
        super().__init__("Invalid Telegram ID.")


class CompanyAdminAssignmentError(CompanyError):
    def __init__(self, message: str = "Company admin assignment error.") -> None:
        super().__init__(message)
