class PublicOnboardingError(Exception):
    """Base exception for public onboarding flow."""


class PaymentCardNotConfiguredError(PublicOnboardingError):
    """Raised when the super admin has not configured a payment card yet."""


class ApplicationNotFoundError(PublicOnboardingError):
    """Raised when an onboarding application is missing."""


class PaymentWindowExpiredError(PublicOnboardingError):
    """Raised when the payment receipt deadline has expired."""


class InvalidApplicationStateError(PublicOnboardingError):
    """Raised when an action is not allowed for the current application status."""
