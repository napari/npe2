import pytest

from npe2.manifest.utils import Version


def test_version():
    v = Version.parse(b"0.1.2")

    assert v == "0.1.2"
    assert v > dict(major=0, minor=1, patch=0)
    assert v <= (0, 2, 0)
    assert v == Version(0, 1, 2)
    assert list(v) == [0, 1, 2, None, None]
    assert str(v) == "0.1.2"

    with pytest.raises(TypeError):
        v == 1.2

    with pytest.raises(ValueError):
        Version.parse("alkfdjs")

    with pytest.raises(TypeError):
        Version.parse(1.2)  # type: ignore
