class CompanyAdminDomainError(Exception):
    """Base company-admin domain exception."""


class BranchAlreadyExistsError(CompanyAdminDomainError):
    def __init__(self, branch_name: str) -> None:
        super().__init__(f"Branch '{branch_name}' already exists.")


class BranchNotFoundError(CompanyAdminDomainError):
    def __init__(self, branch_id: int) -> None:
        super().__init__(f"Branch with id={branch_id} was not found.")


class BranchDeleteRestrictedError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Branch has linked employees and cannot be deleted.")


class DepartmentAlreadyExistsError(CompanyAdminDomainError):
    def __init__(self, department_name: str) -> None:
        super().__init__(f"Department '{department_name}' already exists.")


class DepartmentNotFoundError(CompanyAdminDomainError):
    def __init__(self, department_id: int) -> None:
        super().__init__(f"Department with id={department_id} was not found.")


class DepartmentDeleteRestrictedError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Department has linked employees and cannot be deleted.")


class ShiftAlreadyExistsError(CompanyAdminDomainError):
    def __init__(self, shift_name: str) -> None:
        super().__init__(f"Shift '{shift_name}' already exists.")


class ShiftNotFoundError(CompanyAdminDomainError):
    def __init__(self, shift_id: int) -> None:
        super().__init__(f"Shift with id={shift_id} was not found.")


class ShiftDeleteRestrictedError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Shift has linked employees and cannot be deleted.")


class EmployeeAlreadyExistsError(CompanyAdminDomainError):
    def __init__(self, employee_code: str) -> None:
        super().__init__(f"Employee with code '{employee_code}' already exists.")


class EmployeeNotFoundError(CompanyAdminDomainError):
    def __init__(self, employee_id: int) -> None:
        super().__init__(f"Employee with id={employee_id} was not found.")


class BranchAssignmentRequiredError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Employee must be assigned to a branch.")


class InvalidPhoneError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Invalid phone number.")


class InvalidLatitudeError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Invalid latitude value.")


class InvalidLongitudeError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Invalid longitude value.")


class InvalidRadiusError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Invalid radius value.")


class InvalidWorkDaysError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("Invalid work days value.")


class ForeignEntityScopeError(CompanyAdminDomainError):
    def __init__(self) -> None:
        super().__init__("The selected entity does not belong to the current company.")
