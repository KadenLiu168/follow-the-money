"""Follow the Money — a credential-free evidence Feed with private on-demand Audit and Event Structuring.

Production logic lives under ``src/follow_the_money``. Importing this package
never reads credentials or network state.
"""

__version__ = "0.1.0"

# Schema majors supported by this build. Consumers and producers fail closed
# on unknown or incompatible majors.
SUPPORTED_SCHEMA_MAJOR = 1
