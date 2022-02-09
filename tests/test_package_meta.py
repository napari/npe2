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
