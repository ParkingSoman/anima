from anima.subsystems._common import extract_json


def test_extract_json_plain():
    assert extract_json('{"x": 1}') == {"x": 1}


def test_extract_json_fenced():
    text = "Here is the output:\n```json\n{\"score\": 4}\n```\nthank you"
    assert extract_json(text) == {"score": 4}


def test_extract_json_inline_prose():
    text = "Sure! {\"valence\": -0.3, \"emotion\": \"sad\"} hope that helps"
    assert extract_json(text) == {"valence": -0.3, "emotion": "sad"}


def test_extract_json_garbage():
    assert extract_json("the answer is 42") is None
