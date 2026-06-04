"""Defense system exceptions."""


class WeaponSafetyError(Exception):
    """Raised when a weapon operation is attempted while safed."""
    pass


class EWConfigurationError(Exception):
    """Raised for invalid EW configuration."""
    pass


class APSEngagementError(Exception):
    """Raised for APS engagement failures."""
    pass


class SwarmCommunicationError(Exception):
    """Raised for swarm communication failures."""
    pass


class NavigationError(Exception):
    """Raised for navigation system failures."""
    pass


class ConfigurationError(Exception):
    """Raised for invalid configuration."""
    pass
