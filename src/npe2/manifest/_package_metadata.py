from importlib import metadata
from typing import Literal

from pydantic import BaseModel, Field, constr, model_validator

from npe2._pydantic_util import is_list_type

# https://packaging.python.org/specifications/core-metadata/

MetadataVersion = Literal["1.0", "1.1", "1.2", "2.0", "2.1", "2.2", "2.3"]
_alphanum = "[a-zA-Z0-9]"
PackageName = constr(pattern=f"^{_alphanum}[a-zA-Z0-9._-]*{_alphanum}$")


class PackageMetadata(BaseModel):
    """Pydantic model for standard python package metadata.

    https://www.python.org/dev/peps/pep-0566/
    https://packaging.python.org/pattern/core-metadata/

    The `importlib.metadata` provides the `metadata()` function,
    but it returns a somewhat awkward `email.message.Message` object.
    """

    class Config:
        extra = "ignore"

    # allow str as a fallback in case the metata-version specification has been
    # updated and we haven't updated the code yet
    metadata_version: MetadataVersion | str = Field(
        "1.0", description="Version of the file format"
    )
    name: PackageName = Field(  # type: ignore
        ...,
        description="The name of the distribution. The name field "
        "is the primary identifier for a distribution.",
    )
    # technically there is PackageVersion regex at
    # https://www.python.org/dev/peps/pep-0440/#id81
    # but it will fail on some dev versions, and it's not worth it.
    version: str = Field(
        ...,
        description="A string containing the distribution's version number. "
        "This field must be in the format specified in PEP 440.",
    )
    dynamic: list[str] | None = Field(
        None,
        description="A string containing the name of another core metadata "
        "field. The field names Name and Version may not be specified in this field.",
        min_ver="2.2",
    )
    platform: list[str] | None = Field(
        None,
        description="A Platform specification describing an operating system "
        "supported by the distribution which is not listed in the “Operating System” "
        "Trove classifiers. See “Classifier” below.",
    )
    supported_platform: list[str] | None = Field(
        None,
        description="Binary distributions containing a PKG-INFO file will use the "
        "Supported-Platform field in their metadata to specify the OS and CPU for "
        "which the binary distribution was compiled",
        min_ver="1.1",
    )
    summary: str | None = Field(
        None, description="A one-line summary of what the distribution does."
    )
    description: str | None = Field(
        None,
        description="A longer description of the distribution that can "
        "run to several paragraphs.",
    )
    description_content_type: str | None = Field(
        None,
        description="A string stating the markup syntax (if any) used in the "
        "distribution's description, so that tools can intelligently render the "
        "description. The type/subtype part has only a few legal values: "
        "text/plain, text/x-rst, text/markdown",
        min_ver="2.1",
    )
    keywords: str | None = Field(
        None,
        description="A list of additional keywords, separated by commas, to be used "
        "to assist searching for the distribution in a larger catalog.",
    )
    home_page: str | None = Field(
        None,
        description="A string containing the URL for the distribution's home page.",
    )
    download_url: str | None = Field(
        None,
        description="A string containing the URL from which THIS version of the "
        "distribution can be downloaded.",
        min_ver="1.1",
    )
    author: str | None = Field(
        None,
        description="A string containing the author's name at a minimum; "
        "additional contact information may be provided.",
    )
    author_email: str | None = Field(
        None,
        description="A string containing the author's e-mail address. It can contain "
        "a name and e-mail address in the legal forms for a RFC-822 From: header.",
    )
    maintainer: str | None = Field(
        None,
        description="A string containing the maintainer's name at a minimum; "
        "additional contact information may be provided.",
        min_ver="1.2",
    )
    maintainer_email: str | None = Field(
        None,
        description="A string containing the maintainer's e-mail address. It can "
        "contain a name and e-mail address in the legal forms for a "
        "RFC-822 From: header.",
        min_ver="1.2",
    )
    license: str | None = Field(
        None,
        description="Text indicating the license covering the distribution where the "
        "license is not a selection from the “License” Trove classifiers. See "
        "“Classifier” below. This field may also be used to specify a particular "
        "version of a license which is named via the Classifier field, or to "
        "indicate a variation or exception to such a license.",
    )
    classifier: list[str] | None = Field(
        None,
        description="Each entry is a string giving a single classification value for "
        "the distribution. Classifiers are described in PEP 301, and the Python "
        "Package Index publishes a dynamic list of currently defined classifiers.",
        min_ver="1.1",
    )
    requires_dist: list[str] | None = Field(
        None,
        description="The field format specification was relaxed to accept the syntax "
        "used by popular publishing tools. Each entry contains a string naming some "
        "other distutils project required by this distribution.",
        min_ver="1.2",
    )
    requires_python: str | None = Field(
        None,
        description="This field specifies the Python version(s) that the distribution "
        "is guaranteed to be compatible with. Installation tools may look at this "
        "when picking which version of a project to install. "
        "The value must be in the format specified in Version specifiers (PEP 440).",
        min_ver="1.2",
    )
    requires_external: list[str] | None = Field(
        None,
        description="The field format specification was relaxed to accept the syntax "
        "used by popular publishing tools. Each entry contains a string describing "
        "some dependency in the system that the distribution is to be used. This "
        "field is intended to serve as a hint to downstream project maintainers, and "
        "has no semantics which are meaningful to the distutils distribution.",
        min_ver="1.2",
    )
    project_url: list[str] | None = Field(
        None,
        description="A string containing a browsable URL for the project and a label "
        "for it, separated by a comma.",
        min_ver="1.2",
    )
    provides_extra: list[str] | None = Field(
        None,
        description="A string containing the name of an optional feature. Must be a "
        "valid Python identifier. May be used to make a dependency conditional on "
        "whether the optional feature has been requested.",
        min_ver="2.1",
    )

    # rarely_used
    provides_dist: list[str] | None = Field(None, min_ver="1.2")
    obsoletes_dist: list[str] | None = Field(None, min_ver="1.2")

    @model_validator(mode="before")
    @classmethod
    def _validate_root(cls, values):
        if "metadata_version" not in values:
            min_vers = {"1.0"}
            for n, info in cls.model_fields.items():
                if n in values and info.json_schema_extra is not None:
                    min_vers.add(info.json_schema_extra.get("min_ver", "1.0"))
            values["metadata_version"] = str(max(float(x) for x in min_vers))
        return values

    @classmethod
    def for_package(cls, name: str) -> "PackageMetadata":
        """Get PackageMetadata from a package name."""
        return cls.from_dist_metadata(metadata.metadata(name))

    # note, the metadata.PackageMetadata hint is only valid for py 3.10
    # before that, it was email.message.Message
    @classmethod
    def from_dist_metadata(cls, meta: "metadata.PackageMetadata") -> "PackageMetadata":
        """Generate PackageMetadata from importlib.metadata.PackageMetdata."""
        manys = [n for n, f in cls.model_fields.items() if is_list_type(f.annotation)]
        d: dict[str, str | list[str]] = {}
        # looks like py3.10 changed the public protocol of metadata.PackageMetadata
        # and they don't want you to rely on the Mapping interface... however, the
        # __iter__ method doesn't iterate key value pairs, just keys, and I can't figure
        # out how to get multi-valued fields from that (e.g. Classifier)
        # might need to change this in the future
        for key, value in meta.items():  # type: ignore
            key = _norm(key)
            if key in manys:
                d.setdefault(key, []).append(value)  # type: ignore
            else:
                d[key] = value
        return cls.model_validate(d)

    def __hash__(self) -> int:
        return id(self)


def _norm(string: str) -> str:
    return string.replace("-", "_").replace(" ", "_").lower()
