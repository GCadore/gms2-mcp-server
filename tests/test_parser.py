r"""
test_parser.py — unit tests for GMS2ProjectParser.

Run with:
    cd mcp-serv && python -m pytest ..\tests\ -v
or from the project root:
    python -m pytest tests/ -v  (after adding mcp-serv to PYTHONPATH)
"""

import os

import pytest

from gms2_parser import GMS2ProjectParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_parser(path) -> GMS2ProjectParser:
    return GMS2ProjectParser(str(path))


# ===========================================================================
# scan_project
# ===========================================================================

class TestScanProject:

    def test_returns_project_name(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.scan_project()
        assert "error" not in result
        assert result["project_name"] == gms2_project.name

    def test_total_gml_files_positive(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.scan_project()
        assert result["total_gml_files"] > 0

    def test_categories_contain_expected_keys(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.scan_project()
        categories = result["categories"]
        for expected in ("Objects", "Scripts", "Rooms", "Sprites"):
            assert expected in categories, f"Missing category: {expected}"

    def test_error_path_not_exists(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        parser = make_parser(nonexistent)
        result = parser.scan_project()
        assert "error" in result

    def test_error_no_yyp_file(self, tmp_path):
        # Directory exists but contains no .yyp file
        (tmp_path / "objects").mkdir()
        parser = make_parser(tmp_path)
        result = parser.scan_project()
        assert "error" in result

    def test_objects_assets_populated(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.scan_project()
        assets = result["categories"]["Objects"]["assets"]
        names = [a["name"] for a in assets]
        assert "obj_player" in names
        assert "obj_enemy" in names


# ===========================================================================
# get_gml_content
# ===========================================================================

class TestGetGmlContent:

    def test_returns_correct_content(self, gms2_project):
        parser = make_parser(gms2_project)
        # Fixture uses Create.gml (parser resolves eventtype=0 → "Create.gml")
        path = str(gms2_project / "objects" / "obj_player" / "Create.gml")
        result = parser.get_gml_content(path)
        assert "error" not in result
        assert "speed" in result["content"]
        assert result["line_count"] >= 1

    def test_error_path_traversal(self, gms2_project):
        parser = make_parser(gms2_project)
        # Attempt to escape the project directory
        evil_path = str(gms2_project / ".." / ".." / "etc" / "passwd")
        result = parser.get_gml_content(evil_path)
        assert "error" in result
        assert "denied" in result["error"].lower() or "outside" in result["error"].lower()

    def test_error_file_not_found(self, gms2_project):
        parser = make_parser(gms2_project)
        path = str(gms2_project / "objects" / "obj_player" / "nonexistent.gml")
        result = parser.get_gml_content(path)
        assert "error" in result

    def test_relative_path_within_project(self, gms2_project):
        """relative_path key is set correctly."""
        parser = make_parser(gms2_project)
        path = str(gms2_project / "objects" / "obj_player" / "Create.gml")
        result = parser.get_gml_content(path)
        assert "error" not in result
        assert "relative_path" in result


# ===========================================================================
# get_room_info
# ===========================================================================

class TestGetRoomInfo:

    def test_returns_formatted_info(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_room_info("rm_main")
        assert "error" not in result
        assert result["formatted_info"]  # non-empty string
        assert "rm_main" in result["formatted_info"]

    def test_room_data_has_layers(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_room_info("rm_main")
        assert "error" not in result
        assert len(result["data"]["layers"]) == 2

    def test_error_room_not_found(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_room_info("rm_does_not_exist")
        assert "error" in result

    def test_error_invalid_name_slash(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_room_info("../etc")
        assert "error" in result
        assert "invalid" in result["error"].lower()

    def test_error_invalid_name_space(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_room_info("rm main")
        assert "error" in result


# ===========================================================================
# get_object_info
# ===========================================================================

class TestGetObjectInfo:

    def test_returns_correct_sprite(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_info("obj_player")
        assert "error" not in result
        sprite_id = result["data"].get("spriteId")
        assert sprite_id is not None
        assert sprite_id.get("name") == "spr_player"

    def test_formatted_info_contains_object_name(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_info("obj_player")
        assert "error" not in result
        assert "obj_player" in result["formatted_info"]

    def test_error_object_not_found(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_info("obj_nonexistent")
        assert "error" in result

    def test_error_invalid_name(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_info("obj/player")
        assert "error" in result


# ===========================================================================
# get_object_events
# ===========================================================================

class TestGetObjectEvents:

    def test_returns_two_events_for_obj_player(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_events("obj_player")
        assert "error" not in result
        assert len(result["events"]) == 2

    def test_event_types_create_and_step(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_events("obj_player")
        event_types = {e["event_type"] for e in result["events"]}
        assert "Create" in event_types
        assert "Step" in event_types

    def test_create_event_has_content(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_events("obj_player")
        create_events = [e for e in result["events"] if e["event_type"] == "Create"]
        assert create_events
        assert create_events[0]["content"] is not None
        assert "speed" in create_events[0]["content"]

    def test_step_event_has_content(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_events("obj_player")
        step_events = [e for e in result["events"] if e["event_type"] == "Step"]
        assert step_events
        assert step_events[0]["content"] is not None

    def test_error_invalid_object_name(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_events("obj;player")
        assert "error" in result

    def test_error_object_not_found(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_object_events("obj_ghost")
        assert "error" in result


# ===========================================================================
# get_script_content
# ===========================================================================

class TestGetScriptContent:

    def test_returns_script_content(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_script_content("scr_utils")
        assert "error" not in result
        assert "clamp" in result["content"]
        assert result["line_count"] >= 1

    def test_returns_correct_script_name(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_script_content("scr_utils")
        assert result["script_name"] == "scr_utils"

    def test_error_script_not_found(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_script_content("scr_nonexistent")
        assert "error" in result

    def test_error_invalid_script_name(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_script_content("scr utils")
        assert "error" in result

    def test_error_invalid_name_with_slash(self, gms2_project):
        parser = make_parser(gms2_project)
        result = parser.get_script_content("scr/utils")
        assert "error" in result


# ===========================================================================
# search_in_project
# ===========================================================================

class TestSearchInProject:

    def test_finds_speed_in_obj_player(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.search_in_project("speed")
        assert "error" not in result
        assert result["total_matches"] >= 2  # Create_0.gml and Step.gml

    def test_case_insensitive_by_default(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result_lower = parser.search_in_project("speed")
        result_upper = parser.search_in_project("SPEED")
        assert result_lower["total_matches"] == result_upper["total_matches"]

    def test_case_sensitive_differs(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result_sensitive = parser.search_in_project("SPEED", case_sensitive=True)
        # "SPEED" won't appear in the files (which have lowercase "speed")
        assert result_sensitive["total_matches"] == 0

    def test_error_invalid_regex(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.search_in_project("[invalid regex")
        assert "error" in result

    def test_no_matches_for_unknown_query(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.search_in_project("xyzzy_no_match_here")
        assert "error" not in result
        assert result["total_matches"] == 0

    def test_match_contains_relative_path(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.search_in_project("speed")
        assert result["matches"]
        for m in result["matches"]:
            assert "relative_path" in m
            assert "line" in m


# ===========================================================================
# edit_gml_file
# ===========================================================================

class TestEditGmlFile:

    def test_edits_content_and_creates_backup(self, gms2_project):
        parser = make_parser(gms2_project)
        # Fixture uses Create.gml (parser resolves eventtype=0 → "Create.gml")
        target = str(gms2_project / "objects" / "obj_player" / "Create.gml")
        new_content = "var speed = 99;"
        result = parser.edit_gml_file(target, new_content, create_backup=True)
        assert "error" not in result

        # Content changed
        with open(target, encoding="utf-8") as f:
            assert f.read() == new_content

        # Backup created
        backup = target + ".bak"
        assert os.path.isfile(backup)
        with open(backup, encoding="utf-8") as f:
            assert "5" in f.read()  # original had "speed = 5"

    def test_backup_path_in_result(self, gms2_project):
        parser = make_parser(gms2_project)
        target = str(gms2_project / "objects" / "obj_player" / "Create.gml")
        result = parser.edit_gml_file(target, "// edited", create_backup=True)
        assert result["backup_path"] is not None
        assert result["backup_path"].endswith(".bak")

    def test_no_backup_when_disabled(self, gms2_project):
        parser = make_parser(gms2_project)
        target = str(gms2_project / "objects" / "obj_player" / "Step.gml")
        result = parser.edit_gml_file(target, "x = 0;", create_backup=False)
        assert "error" not in result
        assert result["backup_path"] is None
        assert not os.path.isfile(target + ".bak")

    def test_error_path_traversal(self, gms2_project):
        parser = make_parser(gms2_project)
        evil_path = str(gms2_project / ".." / "evil.gml")
        result = parser.edit_gml_file(evil_path, "// evil", create_backup=False)
        assert "error" in result
        assert "denied" in result["error"].lower() or "outside" in result["error"].lower()

    def test_error_file_not_found(self, gms2_project):
        parser = make_parser(gms2_project)
        missing = str(gms2_project / "objects" / "obj_player" / "missing.gml")
        result = parser.edit_gml_file(missing, "// x")
        assert "error" in result

    def test_line_count_updated(self, gms2_project):
        parser = make_parser(gms2_project)
        # Fixture uses Create.gml (parser resolves eventtype=0 → "Create.gml")
        target = str(gms2_project / "objects" / "obj_enemy" / "Create.gml")
        new_content = "line1\nline2\nline3"
        result = parser.edit_gml_file(target, new_content, create_backup=False)
        assert "error" not in result
        assert result["line_count"] == 3


# ===========================================================================
# find_asset_references
# ===========================================================================

class TestFindAssetReferences:

    def test_finds_speed_in_gml(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.find_asset_references("speed")
        assert "error" not in result
        assert result["total_gml_files"] > 0

    def test_finds_obj_player_in_room(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.find_asset_references("obj_player")
        assert "error" not in result
        assert result["total_rooms"] >= 1
        room_names = [r["room"] for r in result["room_instances"]]
        assert "rm_main" in room_names

    def test_obj_player_instance_count(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.find_asset_references("obj_player")
        rm_main_entry = next(
            (r for r in result["room_instances"] if r["room"] == "rm_main"), None
        )
        assert rm_main_entry is not None
        assert rm_main_entry["instance_count"] == 2  # two obj_player instances in rm_main

    def test_zero_references_for_unknown_asset(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.find_asset_references("xyzzy_no_such_asset")
        assert "error" not in result
        assert result["total_gml_files"] == 0
        assert result["total_rooms"] == 0

    def test_result_has_asset_name_key(self, gms2_project):
        parser = make_parser(gms2_project)
        parser.scan_project()
        result = parser.find_asset_references("clamp")
        assert result["asset_name"] == "clamp"


# ===========================================================================
# _validate_asset_name  (internal but security-critical)
# ===========================================================================

class TestValidateAssetName:

    @pytest.mark.parametrize("name", [
        "obj_player",
        "scr_utils_v2",
        "spr-bullet",
        "Room1",
        "a",
        "obj123",
    ])
    def test_accepts_valid_names(self, gms2_project, name):
        parser = make_parser(gms2_project)
        assert parser._validate_asset_name(name) is True

    @pytest.mark.parametrize("name", [
        "../etc",
        "obj player",   # space
        "obj/player",   # slash
        "obj;player",   # semicolon
        "obj.player",   # dot
        "obj\\player",  # backslash
        "obj*player",   # wildcard
        "",             # empty string
        "obj\nplayer",  # newline
    ])
    def test_rejects_invalid_names(self, gms2_project, name):
        parser = make_parser(gms2_project)
        assert parser._validate_asset_name(name) is False
