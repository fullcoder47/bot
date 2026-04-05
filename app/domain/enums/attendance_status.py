from enum import StrEnum


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    LATE = "LATE"
    ABSENT = "ABSENT"
    EARLY_LEAVE = "EARLY_LEAVE"
    HALF_DAY = "HALF_DAY"
    ON_LEAVE = "ON_LEAVE"
    SICK_LEAVE = "SICK_LEAVE"
    WEEKEND = "WEEKEND"
