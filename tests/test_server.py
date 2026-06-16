"""
test_server.py — unit tests for GMS2MCPServer.

Uses pytest-asyncio for async test functions.
"""

import pytest
import pytest_asyncio  # noqa: F401 – ensure plugin is importable

from mcp_server import GMS2MCPServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_server(project_path=None) -> GMS2MCPServer:
    return GMS2MCPServer(project_path=str(project_path) if project_path else None)


def _text(result) -> str:
    """Extract the text string from the first TextContent in a result list."""
    assert result, "Result list is empty"
    return result[0].text


# ===========================================================================
# get_tools
# ===========================================================================

class TestGetTools:

    def test_returns_12_tools(self):
        server = make_server()
        tools = server.get_tools()
        assert len(tools) == 12

    def test_tool_names_are_unique(self):
        server = make_server()
        names = [t.name for t in server.get_tools()]
        assert len(names) == len(set(names))

    def test_scan_tool_present(self):
        server = make_server()
        names = [t.name for t in server.get_tools()]
        assert "scan_gms2_project" in names

    def test_all_tools_have_input_schema(self):
        server = make_server()
        for tool in server.get_tools():
            assert tool.inputSchema is not None, f"Tool '{tool.name}' missing inputSchema"


# ===========================================================================
# handle_tool_call — unknown tool
# ===========================================================================

class TestUnknownTool:

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        server = make_server()
        result = await server.handle_tool_call("unknown_tool", {})
        text = _text(result)
        assert "unknown" in text.lower() or "error" in text.lower()


# ===========================================================================
# scan_gms2_project
# ===========================================================================

class TestScanProjectTool:

    @pytest.mark.asyncio
    async def test_returns_project_name(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "scan_gms2_project", {"project_path": str(gms2_project)}
        )
        text = _text(result)
        assert "Error" not in text[:10]          # first chars must not be an error prefix
        assert gms2_project.name in text

    @pytest.mark.asyncio
    async def test_includes_total_gml_count(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "scan_gms2_project", {"project_path": str(gms2_project)}
        )
        text = _text(result)
        assert "Total GML Files" in text

    @pytest.mark.asyncio
    async def test_error_nonexistent_path(self):
        server = make_server()
        result = await server.handle_tool_call(
            "scan_gms2_project", {"project_path": "/nonexistent/path/game"}
        )
        text = _text(result)
        assert "Error" in text or "error" in text


# ===========================================================================
# get_script_content
# ===========================================================================

class TestGetScriptContentTool:

    @pytest.mark.asyncio
    async def test_returns_script_content(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "get_script_content",
            {"project_path": str(gms2_project), "script_name": "scr_utils"},
        )
        text = _text(result)
        assert "clamp" in text

    @pytest.mark.asyncio
    async def test_error_nonexistent_script(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "get_script_content",
            {"project_path": str(gms2_project), "script_name": "scr_ghost"},
        )
        text = _text(result)
        assert "Error" in text or "error" in text


# ===========================================================================
# search_in_project
# ===========================================================================

class TestSearchInProjectTool:

    @pytest.mark.asyncio
    async def test_finds_speed(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "search_in_project",
            {"project_path": str(gms2_project), "query": "speed"},
        )
        text = _text(result)
        assert "speed" in text.lower()
        # Should report at least one match
        assert "Total matches:" in text

    @pytest.mark.asyncio
    async def test_no_matches_for_unknown_query(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "search_in_project",
            {"project_path": str(gms2_project), "query": "xyzzy_no_match"},
        )
        text = _text(result)
        assert "No matches found" in text or "Total matches: 0" in text

    @pytest.mark.asyncio
    async def test_error_invalid_regex(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "search_in_project",
            {"project_path": str(gms2_project), "query": "[invalid"},
        )
        text = _text(result)
        assert "Error" in text or "error" in text


# ===========================================================================
# get_object_events
# ===========================================================================

class TestGetObjectEventsTool:

    @pytest.mark.asyncio
    async def test_returns_events_for_obj_player(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "get_object_events",
            {"project_path": str(gms2_project), "object_name": "obj_player"},
        )
        text = _text(result)
        assert "obj_player" in text
        assert "Create" in text or "Step" in text

    @pytest.mark.asyncio
    async def test_error_missing_object_name(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "get_object_events",
            {"project_path": str(gms2_project)},
        )
        text = _text(result)
        assert "Error" in text or "error" in text


# ===========================================================================
# get_room_info
# ===========================================================================

class TestGetRoomInfoTool:

    @pytest.mark.asyncio
    async def test_returns_room_info(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "get_room_info",
            {"project_path": str(gms2_project), "room_name": "rm_main"},
        )
        text = _text(result)
        assert "rm_main" in text
        assert "Error" not in text[:6]

    @pytest.mark.asyncio
    async def test_error_room_not_found(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "get_room_info",
            {"project_path": str(gms2_project), "room_name": "rm_ghost"},
        )
        text = _text(result)
        assert "Error" in text or "error" in text


# ===========================================================================
# find_asset_references
# ===========================================================================

class TestFindAssetReferencesTool:

    @pytest.mark.asyncio
    async def test_finds_obj_player_in_room(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "find_asset_references",
            {"project_path": str(gms2_project), "asset_name": "obj_player"},
        )
        text = _text(result)
        assert "rm_main" in text

    @pytest.mark.asyncio
    async def test_error_missing_asset_name(self, gms2_project):
        server = make_server()
        result = await server.handle_tool_call(
            "find_asset_references",
            {"project_path": str(gms2_project)},
        )
        text = _text(result)
        assert "Error" in text or "error" in text


# ===========================================================================
# Cached parser reuse
# ===========================================================================

class TestCachedParser:

    @pytest.mark.asyncio
    async def test_same_path_reuses_parser(self, gms2_project):
        """Calling twice with the same path should not raise and should reuse cache."""
        server = make_server(gms2_project)
        args = {"project_path": str(gms2_project)}
        r1 = await server.handle_tool_call("scan_gms2_project", args)
        r2 = await server.handle_tool_call("scan_gms2_project", args)
        assert _text(r1) == _text(r2)
