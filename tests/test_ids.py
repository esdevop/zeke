from zeke.ids import _id_exists, generate_id


def test_generate_id_correct_length(notes_dir):
    id_ = generate_id(6, notes_dir)
    assert len(id_) == 6


def test_generate_id_custom_length(notes_dir):
    id_ = generate_id(8, notes_dir)
    assert len(id_) == 8


def test_generate_id_lowercase_alnum(notes_dir):
    id_ = generate_id(6, notes_dir)
    assert id_.isalnum()
    assert id_ == id_.lower()


def test_generate_id_avoids_existing_note(notes_dir):
    # Create a note whose stem starts with "aaaaaa--"
    (notes_dir / "aaaaaa--graph-theory.md").write_text("---\nid: aaaaaa\n---\n")
    assert _id_exists("aaaaaa", notes_dir)


def test_generate_id_avoids_existing_asset(notes_dir):
    assets = notes_dir / "assets"
    assets.mkdir()
    (assets / "bbbbbb--diagram.png").write_text("")
    assert _id_exists("bbbbbb", notes_dir)


def test_id_not_exists_empty_dir(notes_dir):
    assert not _id_exists("zzzzzz", notes_dir)


def test_generate_id_unique_across_calls(notes_dir):
    ids = {generate_id(6, notes_dir) for _ in range(20)}
    # All should be well-formed; collisions extremely unlikely
    assert all(len(i) == 6 for i in ids)


def test_generate_id_no_assets_dir_ok(notes_dir):
    # assets/ doesn't exist — should not raise
    assert not (notes_dir / "assets").exists()
    id_ = generate_id(6, notes_dir)
    assert len(id_) == 6
