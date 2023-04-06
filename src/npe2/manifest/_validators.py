import re

_package_name = "([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])"
_python_identifier = "([a-zA-Z_][a-zA-Z_0-9]*)"

# how do we deal with keywords ?
# do we try to validate ? Or do we just
# assume users won't try to create a command named
# `npe2_tester.False.if.for.in` ?
_identifier_plus_dash = "(?:[a-zA-Z_][a-zA-Z_0-9-]+)"
_dotted_name = f"(?:(?:{_identifier_plus_dash}\\.)*{_identifier_plus_dash})"
PACKAGE_NAME_PATTERN = re.compile(f"^{_package_name}$", re.IGNORECASE)
DOTTED_NAME_PATTERN = re.compile(_dotted_name)
DISPLAY_NAME_PATTERN = re.compile(r"^[^\W_][\w -~:.'\"]{1,88}[^\W_]$")
PYTHON_NAME_PATTERN = re.compile(f"^({_dotted_name}):({_dotted_name})$")
COMMAND_ID_PATTERN = re.compile(
    f"^(({_package_name}\\.)*{_python_identifier})$", re.IGNORECASE
)


def command_id(id: str) -> str:
    if id and not COMMAND_ID_PATTERN.match(id):
        raise ValueError(
            f"{id!r} is not a valid command id. It must begin with the package name "
            "followed by a period, then may can only contain alphanumeric "
            "characters and underscores."
        )
    return id


def package_name(name: str) -> str:
    """Assert that `name` is a valid package name in accordance with PEP-0508."""
    if name and not PACKAGE_NAME_PATTERN.match(name):
        raise ValueError(
            f"{name!r} is not a valid python package name. "
            "See https://peps.python.org/pep-0508/#names "
        )
    return name


def python_name(name: str) -> str:
    """Assert that `name` is a valid python name: e.g. `module.submodule:funcname`"""
    if name and not PYTHON_NAME_PATTERN.match(name):
        msg = (
            f"{name!r} is not a valid python_name.  A python_name must "
            "be of the form '{obj.__module__}:{obj.__qualname__}' (e.g. "
            "'my_package.a_module:some_function')."
        )
        if ".<locals>." in name:
            *_, a, b = name.split(".<locals>.")
            a = a.split(":")[-1]
            msg += (
                " Note: functions defined in local scopes are not yet supported. "
                f"Please move function {b!r} to the global scope of module {a!r}"
            )
        raise ValueError(msg)
    return name


def display_name(v: str) -> str:
    if not DISPLAY_NAME_PATTERN.match(v):
        raise ValueError(
            f"{v} is not a valid display_name. It must be 3-90 characters long, "
            "and must not begin or end with an underscore, white space, or "
            "non-word character."
        )
    return v


def icon_path(v: str) -> str:
    if not v:
        return ""
    if v.startswith("http"):
        if not v.startswith("https://"):
            raise ValueError(
                f"{v} is not a valid icon URL. It must start with 'https://'"
            )
        return v
    assert isinstance(v, str), f"{v} must be a string"
    return v
