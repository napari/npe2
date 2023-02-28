from npe2 import PackageMetadata


def test_package_metadata_version():
    """Test that we intelligently pick the min required metadata version"""
    assert PackageMetadata(name="test", version="1.0").metadata_version == "1.0"
    pm2 = PackageMetadata(name="test", version="1.0", maintainer="bob")
    assert pm2.metadata_version == "1.2"
    pm3 = PackageMetadata(
        name="test",
        version="1.0",
        maintainer="bob",
        description_content_type="text/markdown",
    )
    assert pm3.metadata_version == "2.1"


def test_hashable():
    hash(PackageMetadata(name="test", version="1.0"))


def test_package_metadata_extra_field():
    pkg = {
        "name": "test",
        "version": "1.0",
        "maintainer": "bob",
        "extra_field_that_is_definitely_not_in_the_model": False,
    }

    try:
        p = PackageMetadata(**pkg)
    except Exception as e:
        raise AssertionError(
            "failed to parse PackageMetadata from a dict with an extra field"
        ) from e

    assert p.name == "test"
    assert p.version == "1.0"
    assert p.maintainer == "bob"
    assert not hasattr(p, "extra_field_that_is_definitely_not_in_the_model")
