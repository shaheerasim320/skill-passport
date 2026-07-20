import json

from skill_passport_core.reasoner import SCHEMA_PATH


def test_packaged_verdict_schema_exists_and_is_valid_json():
    assert SCHEMA_PATH.is_file()
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["type"] == "object"
