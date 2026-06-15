"""
conftest.py — shared fixtures for the GMS2 MCP Server test suite.

Adds mcp-serv/ to sys.path so that gms2_parser and mcp_server can be imported
when pytest is launched from any directory.
"""

import json
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Ensure the mcp-serv package directory is on sys.path so imports work.
# ---------------------------------------------------------------------------
_MPCSERV_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "mcp-serv")
)
if _MPCSERV_DIR not in sys.path:
    sys.path.insert(0, _MPCSERV_DIR)


# ---------------------------------------------------------------------------
# Fixture: gms2_project
# ---------------------------------------------------------------------------

@pytest.fixture()
def gms2_project(tmp_path):
    """
    Creates a minimal but structurally valid GMS2 project in a temporary
    directory and returns its path.

    Layout
    ------
    <tmp>/
      MyGame.yyp
      objects/
        obj_player/
          obj_player.yy
          Create_0.gml       <- "var speed = 5;"
          Step.gml           <- "x += speed;"
        obj_enemy/
          obj_enemy.yy
          Create_0.gml       <- "hp = 10;"
      scripts/
        scr_utils/
          scr_utils.gml
      rooms/
        rm_main/
          rm_main.yy
      sprites/
        spr_player/
          spr_player.yy
          frame0.png         <- empty placeholder
    """

    root = tmp_path

    # ---- .yyp ----------------------------------------------------------------
    (root / "MyGame.yyp").write_text("{}", encoding="utf-8")

    # ---- objects/obj_player --------------------------------------------------
    obj_player_dir = root / "objects" / "obj_player"
    obj_player_dir.mkdir(parents=True)

    obj_player_yy = {
        "name": "obj_player",
        "spriteId": {"name": "spr_player"},
        "parentObjectId": None,
        "visible": True,
        "solid": False,
        "persistent": False,
        "physicsObject": False,
        "eventList": [
            {"eventtype": 0, "enumb": 0},
            {"eventtype": 3, "enumb": 0},
        ],
        "properties": [],
    }
    (obj_player_dir / "obj_player.yy").write_text(
        json.dumps(obj_player_yy, indent=2), encoding="utf-8"
    )
    # GMS2ProjectParser resolves eventtype=0 (Create) to "Create.gml" (not "Create_0.gml")
    (obj_player_dir / "Create.gml").write_text("var speed = 5;", encoding="utf-8")
    (obj_player_dir / "Step.gml").write_text("x += speed;", encoding="utf-8")

    # ---- objects/obj_enemy ---------------------------------------------------
    obj_enemy_dir = root / "objects" / "obj_enemy"
    obj_enemy_dir.mkdir(parents=True)

    obj_enemy_yy = {
        "name": "obj_enemy",
        "spriteId": None,
        "parentObjectId": None,
        "visible": True,
        "solid": False,
        "persistent": False,
        "physicsObject": False,
        "eventList": [
            {"eventtype": 0, "enumb": 0},
        ],
        "properties": [],
    }
    (obj_enemy_dir / "obj_enemy.yy").write_text(
        json.dumps(obj_enemy_yy, indent=2), encoding="utf-8"
    )
    # Parser resolves eventtype=0 → "Create.gml"
    (obj_enemy_dir / "Create.gml").write_text("hp = 10;", encoding="utf-8")

    # ---- scripts/scr_utils ---------------------------------------------------
    scr_utils_dir = root / "scripts" / "scr_utils"
    scr_utils_dir.mkdir(parents=True)
    (scr_utils_dir / "scr_utils.gml").write_text(
        "function clamp(v, lo, hi) { return max(lo, min(hi, v)); }",
        encoding="utf-8",
    )

    # ---- rooms/rm_main -------------------------------------------------------
    rm_main_dir = root / "rooms" / "rm_main"
    rm_main_dir.mkdir(parents=True)

    rm_main_yy = {
        "name": "rm_main",
        "roomSettings": {"Width": 1024, "Height": 768, "Speed": 60},
        "isPersistent": False,
        "layers": [
            {
                "name": "Instances",
                "__type": "GMInstanceLayer",
                "instances": [
                    {"objId": {"name": "obj_player"}},
                    {"objId": {"name": "obj_player"}},
                    {"objId": {"name": "obj_enemy"}},
                ],
            },
            {
                "name": "Background",
                "__type": "GMBackgroundLayer",
                "instances": [],
            },
        ],
    }
    (rm_main_dir / "rm_main.yy").write_text(
        json.dumps(rm_main_yy, indent=2), encoding="utf-8"
    )

    # ---- sprites/spr_player --------------------------------------------------
    spr_player_dir = root / "sprites" / "spr_player"
    spr_player_dir.mkdir(parents=True)

    spr_player_yy = {"name": "spr_player"}
    (spr_player_dir / "spr_player.yy").write_text(
        json.dumps(spr_player_yy, indent=2), encoding="utf-8"
    )
    (spr_player_dir / "frame0.png").write_bytes(b"")   # empty placeholder

    return root
