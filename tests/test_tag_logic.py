from app.services.tag_logic import tags_for_upload


def test_tags_for_upload_basic():
    cats, upload = tags_for_upload(["Creator:John Doe", "character:Alice", "misc_tag"])  # mixed case
    assert 'creator' in cats and 'john_doe' in cats['creator']
    assert 'character' in cats and 'alice' in cats['character']
    assert 'default' in cats
    assert 'john_doe' in upload and 'alice' in upload and 'misc_tag' in upload
