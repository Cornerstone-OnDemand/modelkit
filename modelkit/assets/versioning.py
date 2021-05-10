import re

VERSION_RE = r"(?P<major>[0-9]+)(.(?P<minor>[0-9]+))?"


class VersionError(Exception):
    pass


class InvalidVersionError(VersionError):
    def __init__(self, version_str):
        super().__init__(f"Version string `{version_str}` is not valid.")


class InvalidMajorVersionError(VersionError):
    def __init__(self, version_str):
        super().__init__(f"Major version string `{version_str}` is not valid.")


class MajorVersionDoesNotExistError(VersionError):
    def __init__(self, version_str):
        super().__init__(f"Major version `{version_str}` not present.")


def parse_version(version_str):
    m = re.fullmatch(VERSION_RE, version_str)
    if not m:
        raise InvalidVersionError(version_str)
    d = m.groupdict()
    return (int(d["major"]), int(d["minor"]) if d.get("minor") else None)


def increment_version(versions_list, major=None, bump_major=False):
    if bump_major:
        version = latest_version(versions_list)
    else:
        version = latest_version(versions_list, major=major)
    version_tuple = parse_version(version)
    v_major = version_tuple[0]
    v_minor = version_tuple[1]
    if bump_major:
        v_major += 1
        v_minor = 0
    else:
        v_minor += 1
    return f"{v_major}.{v_minor}"


def sort_versions(versions_list):
    def _key(v):
        maj_v, min_v = parse_version(v)
        if min_v is None:
            min_v = 0
        return maj_v, min_v

    return sorted(versions_list, reverse=True, key=_key)


def filter_versions(versions_list, major):
    if not re.fullmatch("[0-9]+", major):
        raise InvalidMajorVersionError(major)
    return [v for v in versions_list if re.match(f"^{major}" + r".", v)]


def latest_version(versions_list, major=None):
    if major:
        l = list(filter_versions(versions_list, major))
        if not l:
            raise MajorVersionDoesNotExistError(major)
        return sort_versions(l)[0]
    return sort_versions(versions_list)[0]
