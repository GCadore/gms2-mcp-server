# GMS2 MCP Server

MCP server for working with GameMaker Studio 2 projects in Cursor IDE and Claude.

## What is this?

This MCP server parses and extracts information from GameMaker Studio 2 projects, providing developers and AI agents with fast access to project structure, GML code, and asset metadata — without opening GameMaker Studio 2.

**Key features:**
- For developers: export all project data in a readable format for study and analysis
- For AI agents: rapid project structure understanding, significantly accelerating vibe-coding
- Deep analysis: automatic scanning of objects, scripts, rooms, sprites, and their relationships
- Write support: edit GML files directly through the AI agent, with automatic backups

## Project Structure

```
gms2-mcp-server/
├── mcp-serv/
│   ├── mcp_server.py       # MCP server with 12 tools
│   └── gms2_parser.py      # GameMaker Studio 2 project parser
├── docs/
│   ├── README.md           # Documentation in English
│   └── README_RU.md        # Documentation in Russian
├── requirements.txt        # Dependencies (mcp==1.11.0, python-dotenv==1.1.1)
└── venv/                   # Python virtual environment (created by user)

Additionally, the user creates:
└── .cursor/mcp.json        # Cursor IDE configuration (includes project path)
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Atennebris/gms2-mcp-server
cd gms2-mcp-server
```

### 2. Create a virtual environment

```bash
# Create venv
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**Current dependencies:**
- `mcp==1.11.0` — official Python SDK for Model Context Protocol
- `python-dotenv==1.1.1` — loading configuration from .env files

### 4. Configure Cursor IDE

Create a `.cursor/mcp.json` file in your project root with the following content:

```json
{
  "mcpServers": {
    "gms2-mcp": {
      "command": "python",
      "args": ["C:/Users/YourName/Desktop/gms2-mcp-server/mcp-serv/mcp_server.py"],
      "env": {
        "GMS2_PROJECT_PATH": "C:/Users/YourName/Downloads/Your GMS2 Project"
      }
    }
  }
}
```

**Important:**
- Replace the path in `args` with the absolute path to the `mcp-serv/mcp_server.py` file.
- Replace the path in `env.GMS2_PROJECT_PATH` with the absolute path to the folder containing your `.yyp` file.
- Use forward slashes `/` even on Windows.

**Alternative — global configuration (all projects):**
1. In Cursor IDE, open Settings.
2. Go to **Tools & Integrations**.
3. Click **New MCP Server** at the bottom.
4. This opens the global `mcp.json` file — add the same configuration there.

**Launch sequence:**
1. Cursor IDE starts `python mcp-serv/mcp_server.py`.
2. `mcp_server.py` reads `GMS2_PROJECT_PATH` from the environment (set in `mcp.json`). Optionally, a `config.env` file in the same directory as the server can also provide this value.
3. `gms2_parser.py` handles all parsing. The parser instance is cached for the session — it is not recreated on every call.

### 5. Restart Cursor IDE

After saving the configuration, restart Cursor IDE and verify that the MCP server shows a green status.

---

## Configuration

The server resolves the project path in this order of priority:

1. `--project-path` CLI argument (for manual testing).
2. `GMS2_PROJECT_PATH` environment variable (set in `mcp.json`).
3. `GMS2_PROJECT_PATH` key in `mcp-serv/config.env` (optional fallback file).
4. `project_path` argument passed directly to a tool call.

For normal usage with Cursor IDE, only step 2 is needed — configure everything in `mcp.json`.

---

## Tools

After successful setup, **12 tools** are available:

---

### 1. `scan_gms2_project`

Scans the GMS2 project directory and returns the full asset structure: objects, scripts, rooms, sprites, fonts, sounds, and more. Includes a count of GML files per asset and a list of recently modified GML files.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `project_path` | No | Path to the GMS2 project folder (falls back to configured path) |

---

### 2. `get_gml_file_content`

Reads and returns the full content of a specific GML file, along with its line count and relative path.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `file_path` | Yes | Path to the GML file (relative to project root or absolute) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 3. `get_room_info`

Returns detailed information about a room parsed from its `.yy` file: layers, instances placed in the room, room settings, and dimensions.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `room_name` | Yes | Name of the room (e.g. `rm_level1`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 4. `get_object_info`

Returns metadata about a GMS2 object from its `.yy` file: assigned sprite, parent object, physics settings, and variable definitions.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `object_name` | Yes | Name of the object (e.g. `obj_player`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 5. `get_sprite_info`

Returns information about a sprite: its path, whether a `.yy` file exists, and the list of frame PNG files.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `sprite_name` | Yes | Name of the sprite (e.g. `spr_player`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 6. `export_project_data`

Exports all project data — objects, scripts, rooms, GML code — to a single text block. Equivalent to the vibe2gml export function. Can optionally write the result to a file.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `save_to_file` | No | If `true`, writes the export to a file instead of returning it (default: `false`) |
| `output_file` | No | File path for the export output (used only when `save_to_file` is `true`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 7. `list_project_assets`

Lists all assets in the project by category, with GML file counts. Supports filtering by a single category.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `category` | No | Filter by category: `Objects`, `Scripts`, `Rooms`, `Sprites`, `Notes`, `Tile Sets`, `Timelines`, `Fonts`, `Sounds`, `Extensions` |
| `project_path` | No | Path to the GMS2 project folder |

---

### 8. `search_in_project`

Searches for a text string or regular expression across all GML files in the project. Returns matching file names, line numbers, and the matched text.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `query` | Yes | Text or regular expression to search for |
| `case_sensitive` | No | Whether the search is case-sensitive (default: `false`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 9. `get_object_events`

Returns all events defined for a GMS2 object together with the full GML code of each event. Useful for understanding object behaviour in one call.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `object_name` | Yes | Name of the object (e.g. `obj_enemy`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 10. `get_script_content`

Reads the GML content of a script asset by name, without needing to know the file path.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `script_name` | Yes | Name of the script (e.g. `scr_utils`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 11. `edit_gml_file`

Overwrites the content of an existing GML file with new content. Automatically creates a `.bak` backup before writing unless disabled.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `file_path` | Yes | Path to the GML file to edit (relative or absolute) |
| `new_content` | Yes | New GML content to write |
| `create_backup` | No | Create a `.bak` backup before saving (default: `true`) |
| `project_path` | No | Path to the GMS2 project folder |

---

### 12. `find_asset_references`

Finds all references to an asset (object, script, sprite, etc.) across GML files and rooms. Returns file names, line numbers, and room instance counts.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `asset_name` | Yes | Name of the asset to search for (e.g. `obj_player`) |
| `project_path` | No | Path to the GMS2 project folder |

---

## Security

The server includes several protections against misuse:

- **Asset name validation** — all asset name parameters are checked against `[a-zA-Z0-9_-]`. Names containing path separators or other special characters are rejected.
- **Path boundary enforcement** — before reading or writing any file, the server resolves the real path via `os.path.realpath` and confirms it is inside the project directory. Requests pointing outside the project tree are rejected with an access-denied error.
- **Error isolation** — internal exceptions are logged server-side (to stderr via the `logging` module) and are not exposed in full to the caller. The user receives a generic error message.

---

## Usage Examples

In Cursor IDE or with Claude, you can ask:

```
"Show me the structure of my GMS2 project"
"Read the code for obj_player"
"What rooms are in the project?"
"Search for 'instance_create' across all GML files"
"Show all events for obj_enemy with their code"
"Read the script scr_collision_utils"
"Find all references to spr_player in the project"
"Edit objects/obj_player/Step_0.gml and replace the movement logic"
"Export all project data for review"
```

---

## System Requirements

- **Python:** 3.8+ (recommended 3.10+; tested on 3.12)
- **GameMaker Studio 2:** Any version with `.yyp` projects
- **Cursor IDE:** With MCP support (or any MCP-compatible client)
- **OS:** Windows 10/11 (tested); Linux/Mac should work

---

## Troubleshooting

### MCP server shows red status
1. Check the absolute path in `args` inside `.cursor/mcp.json`.
2. Check that `GMS2_PROJECT_PATH` points to the folder containing the `.yyp` file.
3. Verify that the virtual environment is activated and dependencies are installed.

### Server cannot find the project
1. Confirm the path in `GMS2_PROJECT_PATH` exists and contains a `.yyp` file.
2. Use forward slashes `/` even on Windows.

### Tools not displayed (0 tools)
1. Restart Cursor IDE.
2. Confirm the Python interpreter is accessible from the terminal.
3. Test the server manually: `python mcp-serv/mcp_server.py`

---

## Architecture Notes

The server is built around two components:

- **`mcp-serv/gms2_parser.py`** — parses `.yyp` and `.yy` files, scans GML files, and implements all data retrieval and write logic.
- **`mcp-serv/mcp_server.py`** — wraps the parser as an MCP server. Handles tool dispatch, input validation, path resolution, and centralised error handling. The parser is instantiated once per session and cached.

Logging is done via the standard `logging` module to stderr. By default only `WARNING` and above are shown. Set the log level to `DEBUG` in the source if you need verbose output during development.

---

## Project History

This MCP server was created based on the idea and functionality of the [vibe2gml](https://github.com/zsturg/vibe2gml) project, which exports GMS2 projects to text format for use with AI agents. This server extends that concept with:

- Direct integration with Cursor IDE and Claude via the MCP protocol
- A richer set of tools (12 vs. the original export-only approach)
- Real-time data access without file export
- Write support for GML files

---

## Additional Resources

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — official SDK
- [MCP Documentation](https://modelcontextprotocol.io/introduction) — protocol documentation
- [GameMaker Studio 2](https://gamemaker.io/) — official GameMaker website
- [vibe2gml](https://github.com/zsturg/vibe2gml) — original project that inspired this server
