import logging as std_logging
import warnings

warnings.filterwarnings(
    "ignore",
    "Your application has authenticated using end user "
    "credentials from Google Cloud SDK..*",
    UserWarning,
)

# Hide filelock info logs, we don't care about acquires/releases
std_logging.getLogger("filelock").setLevel(std_logging.ERROR)
