"""Follow the Money — a credential-free five-domain Evidence Feed.

Production logic lives under ``src/follow_the_money/feed``. Importing this
package never reads credentials or network state.
"""

__version__ = "0.1.0"

# Application configuration schema major. Feed logical and artifact majors
# are owned by ``follow_the_money.feed``.
SUPPORTED_SCHEMA_MAJOR = 1
