from repo_presenter.readme.composition.references import positional_only

LONG = (
    "Additional Examples below extends this into a from-scratch showcase "
    "([`examples/12_create_features.cpp`](examples/12_create_features.cpp) builds a document with "
    "Table/Row/Cell layouts, drawing shapes, AcroForm fields, encryption, and page stamps, "
    "then saves it) so you can see every creation feature in one runnable program."
)


def test_a_long_content_rich_sentence_with_a_pointer_phrase_is_not_positional_only() -> None:
    assert not positional_only(LONG)


def test_a_link_to_a_file_makes_a_short_pointer_content() -> None:
    assert not positional_only("See the examples below: [demo](examples/demo.cpp).")


def test_inline_code_beyond_a_bare_pointer_is_content() -> None:
    assert not positional_only("The `Table` API is shown in the example below.")


def test_a_long_pointer_sentence_is_content() -> None:
    words = " ".join(["word"] * 30)
    assert not positional_only(f"The table below lists {words}.")


def test_short_pointers_stay_positional_only() -> None:
    assert positional_only("See the table below.")
    assert positional_only("The methods are listed in the table below.")
    assert positional_only("Details are in the table below ([API](#api-reference)).")
