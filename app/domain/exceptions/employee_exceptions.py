from app.domain.exceptions.company_admin_exceptions import EmployeeNotFoundError


class EmployeeAuthError(Exception):
    """Base employee access exception."""


class EmployeeInactiveError(EmployeeAuthError):
    def __init__(self) -> None:
        super().__init__("Employee is inactive.")


class EmployeeBranchNotAssignedError(EmployeeAuthError):
    def __init__(self) -> None:
        super().__init__("Employee branch is not assigned.")


class EmployeeShiftNotAssignedError(EmployeeAuthError):
    def __init__(self) -> None:
        super().__init__("Employee shift is not assigned.")
