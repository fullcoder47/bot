class AttendanceError(Exception):
    """Base attendance exception."""


class AttendanceSessionExpiredError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Attendance session has expired.")


class AttendanceSessionNotFoundError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Attendance session was not found.")


class AttendanceSessionConflictError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Another attendance session is already open.")


class AttendanceAlreadyCheckedInError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Employee has already checked in today.")


class AttendanceAlreadyCheckedOutError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Employee has already checked out today.")


class AttendanceCheckOutWithoutCheckInError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Cannot check out without check-in.")


class BranchLocationNotConfiguredError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Branch location is not configured.")


class LocationVerificationFailedError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Location verification failed.")


class VideoNoteRequiredError(AttendanceError):
    def __init__(self) -> None:
        super().__init__("Video note is required.")


class LeaveRequestValidationError(AttendanceError):
    def __init__(self, message: str = "Leave request is invalid.") -> None:
        super().__init__(message)
