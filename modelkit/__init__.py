import warnings

from modelkit.core.library import ModelLibrary, load_model  # NOQA

# Silence Tensorflow warnings
# https://github.com/tensorflow/tensorflow/issues/30427
warnings.simplefilter(action="ignore", category=FutureWarning)


__version__ = "0.0.1"
