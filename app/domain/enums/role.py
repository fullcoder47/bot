from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    COMPANY_ADMIN = "COMPANY_ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"
