try:
    import numpy as np

    has_numpy = True
except ModuleNotFoundError:  # pragma: no cover
    has_numpy = False


def safe_np_dump(obj):
    if has_numpy:
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
    return obj
