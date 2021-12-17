import re

# how do we deal with keywords ?
# do we try to validate ? Or do we just
# assume users won't try to create a command named
# `npe2_tester.False.if.for.in` ?
_identifier_plus_dash = "(?:[a-zA-Z_][a-zA-Z_0-9-]+)"
_dotted_name = f"(?:(?:{_identifier_plus_dash}\\.)*{_identifier_plus_dash})"
PYTHON_NAME_PATTERN = re.compile(f"^({_dotted_name}):({_dotted_name})$")
DOTTED_NAME_PATTERN = re.compile(_dotted_name)


def python_name(name: str) -> str:
    """Assert that `name` is a valid python name: e.g. `module.submodule:funcname`"""
    if name and not PYTHON_NAME_PATTERN.match(name):
        raise ValueError(
            f"{name} is not a valid python_name.  A python_name must "
            "be of the form `{obj.__module__}:{obj.__qualname__} `(e.g. "
            "`my_package.a_module:some_function`). "
        )
    return name
