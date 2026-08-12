"""Follow the Money — a deterministic, script-first daily financial intelligence pipeline.

The package exposes the ``follow-the-money`` console entry points and keeps all
production logic under ``src/follow_the_money``. Importing this package never
reads credentials or network state.
"""

__version__ = "0.1.0"

# Schema majors supported by this build. Consumers and producers fail closed
# on unknown or incompatible majors.
SUPPORTED_SCHEMA_MAJOR = 1
