from repo_presenter import __version__


def test_version_is_nonempty():
    assert __version__
    assert isinstance(__version__, str)
