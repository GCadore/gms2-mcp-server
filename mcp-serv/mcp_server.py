#!/usr/bin/env python3
"""
MCP Server for GameMaker Studio 2 projects.
Provides tools for parsing and analysing GMS2 project files.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from gms2_parser import GMS2ProjectParser

logger = logging.getLogger(__name__)


class GMS2MCPServer:
    """MCP Server for GameMaker Studio 2 projects."""

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = project_path
        self._cached_parser: Optional[GMS2ProjectParser] = None
        if project_path:
            self._cached_parser = GMS2ProjectParser(project_path)
        logger.debug("GMS2MCPServer initialised with project_path: %s", project_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error(message: str) -> List[TextContent]:
        return [TextContent(type="text", text=f"Error: {message}")]

    def _path_from_config(self) -> Optional[str]:
        """Loads project path from config.env, if present."""
        config_file = os.path.join(os.path.dirname(__file__), 'config.env')
        load_dotenv(config_file)
        return os.getenv('GMS2_PROJECT_PATH')

    def _get_project_path(self, arguments: Dict[str, Any]) -> str:
        """Resolves the project path from arguments, instance state, or config.env."""
        provided_path = arguments.get("project_path")

        # Treat missing path or the MCP server's own directory as "not provided"
        is_server_dir = (
            provided_path
            and os.path.abspath(provided_path) == os.path.abspath(os.getcwd())
        )
        if not provided_path or is_server_dir:
            if self.project_path:
                return self.project_path
            config_path = self._path_from_config()
            if config_path:
                logger.debug("Loaded project path from config.env: %s", config_path)
                return config_path
            raise ValueError(
                "Project path not configured. "
                "Set GMS2_PROJECT_PATH in config.env or pass the project_path argument."
            )

        return provided_path

    def _get_parser(self, arguments: Dict[str, Any]) -> GMS2ProjectParser:
        """Returns a cached parser for the resolved project path."""
        project_path = self._get_project_path(arguments)
        abs_path = os.path.abspath(project_path)
        if self._cached_parser is None or self._cached_parser.project_path != abs_path:
            logger.debug("Creating new parser for: %s", abs_path)
            self._cached_parser = GMS2ProjectParser(project_path)
        return self._cached_parser

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="scan_gms2_project",
                description="Сканирует проект GameMaker Studio 2 и возвращает структуру файлов",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_gml_file_content",
                description="Получает содержимое конкретного GML файла",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Путь к GML файлу (относительный ou absoluto)"
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            Tool(
                name="get_room_info",
                description="Получает детальную информацию о комнате из .yy файла",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "room_name": {
                            "type": "string",
                            "description": "Имя комнаты"
                        }
                    },
                    "required": ["room_name"]
                }
            ),
            Tool(
                name="get_object_info",
                description="Получает детальную информацию об объекте из .yy файла",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "object_name": {
                            "type": "string",
                            "description": "Имя объекта"
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            Tool(
                name="get_sprite_info",
                description="Получает информацию о спрайте",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "sprite_name": {
                            "type": "string",
                            "description": "Имя спрайта"
                        }
                    },
                    "required": ["sprite_name"]
                }
            ),
            Tool(
                name="export_project_data",
                description="Экспортирует все данные проекта в текстовый формат (аналог функции из vibe2gml)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "save_to_file": {
                            "type": "boolean",
                            "description": "Сохранить результат в файл (по умолчанию false)",
                            "default": False
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Путь для сохранения файла (если save_to_file=true)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="list_project_assets",
                description="Получает список всех ассетов проекта по категориям",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "category": {
                            "type": "string",
                            "description": "Фильтр по категории (Objects, Scripts, Rooms, Sprites, etc.)",
                            "enum": ["Objects", "Scripts", "Rooms", "Sprites", "Notes", "Tile Sets", "Timelines", "Fonts", "Sounds", "Extensions"]
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="search_in_project",
                description="Busca texto ou regex em todos os arquivos GML do projeto",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "query": {
                            "type": "string",
                            "description": "Texto ou expressão regular a buscar"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Busca sensível a maiúsculas/minúsculas (padrão: false)",
                            "default": False
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Número de linhas de contexto antes/depois do match (padrão: 0)",
                            "default": 0,
                            "minimum": 0,
                            "maximum": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_object_events",
                description="Retorna todos os eventos de um objeto com o código GML de cada um",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "object_name": {
                            "type": "string",
                            "description": "Nome do objeto GMS2"
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            Tool(
                name="get_script_content",
                description="Retorna o conteúdo GML de um script pelo nome",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "script_name": {
                            "type": "string",
                            "description": "Nome do script GMS2"
                        }
                    },
                    "required": ["script_name"]
                }
            ),
            Tool(
                name="edit_gml_file",
                description="Sobrescreve o conteúdo de um arquivo GML existente",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Caminho do arquivo GML (relativo ou absoluto)"
                        },
                        "new_content": {
                            "type": "string",
                            "description": "Novo conteúdo GML para o arquivo"
                        },
                        "create_backup": {
                            "type": "boolean",
                            "description": "Criar backup .bak antes de salvar (padrão: true)",
                            "default": True
                        }
                    },
                    "required": ["file_path", "new_content"]
                }
            ),
            Tool(
                name="find_asset_references",
                description="Encontra todas as referências a um asset (objeto, script, sprite) no projeto",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Путь к папке проекта GMS2 (необязательно, используется из config.env)"
                        },
                        "asset_name": {
                            "type": "string",
                            "description": "Nome do asset a procurar"
                        }
                    },
                    "required": ["asset_name"]
                }
            ),
        ]

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatches tool calls; centralises error handling."""
        try:
            if name == "scan_gms2_project":
                return await self._scan_project(arguments)
            elif name == "get_gml_file_content":
                return await self._get_gml_content(arguments)
            elif name == "get_room_info":
                return await self._get_room_info(arguments)
            elif name == "get_object_info":
                return await self._get_object_info(arguments)
            elif name == "get_sprite_info":
                return await self._get_sprite_info(arguments)
            elif name == "export_project_data":
                return await self._export_project_data(arguments)
            elif name == "list_project_assets":
                return await self._list_project_assets(arguments)
            elif name == "search_in_project":
                return await self._search_project(arguments)
            elif name == "get_object_events":
                return await self._get_object_events(arguments)
            elif name == "get_script_content":
                return await self._get_script_content(arguments)
            elif name == "edit_gml_file":
                return await self._edit_gml_file(arguments)
            elif name == "find_asset_references":
                return await self._find_asset_references(arguments)
            else:
                return self._error(f"Unknown tool: {name}")
        except ValueError as e:
            return self._error(str(e))
        except Exception as e:
            logger.exception("Unhandled error in tool '%s'", name)
            return self._error(f"Unexpected error in {name}: {str(e)}")

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _scan_project(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        result = parser.scan_project()

        if "error" in result:
            return self._error(result["error"])

        output = [
            f"GameMaker Studio 2 Project: {result['project_name']}",
            f"Path: {result['project_path']}",
            f"Total GML Files: {result['total_gml_files']}",
            "",
        ]

        for category, info in result['categories'].items():
            if info['assets']:
                output.append(f"{category}: {len(info['assets'])} assets")
                for asset in info['assets']:
                    gml_count = len(asset['gml_files'])
                    yy_status = "✓" if asset['yy_file'] else "✗"
                    output.append(f"  - {asset['name']} (GML: {gml_count}, YY: {yy_status})")

        output.extend(["", "Recent GML Files:"])
        for i, (display_name, _, relative_path, _) in enumerate(result['gml_files'][:10]):
            output.append(f"  {i+1}. {display_name} ({relative_path})")

        if len(result['gml_files']) > 10:
            output.append(f"  ... and {len(result['gml_files']) - 10} more files")

        return [TextContent(type="text", text="\n".join(output))]

    async def _get_gml_content(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        project_path = parser.project_path

        file_path = arguments.get("file_path")
        if not file_path:
            return self._error("file_path is required")

        if not os.path.isabs(file_path):
            file_path = os.path.join(project_path, file_path)

        # Enforce project boundary before handing off to the parser
        resolved = os.path.realpath(os.path.abspath(file_path))
        project_real = os.path.realpath(project_path)
        if not (resolved == project_real or resolved.startswith(project_real + os.sep)):
            return self._error("Access denied: file path is outside the project directory")

        result = parser.get_gml_content(file_path)

        if "error" in result:
            return self._error(result["error"])

        output = [
            f"GML File: {result['relative_path']}",
            f"Lines: {result['line_count']}",
            "-" * 50,
            result['content'],
        ]
        return [TextContent(type="text", text="\n".join(output))]

    async def _get_room_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        room_name = arguments.get("room_name")
        if not room_name:
            return self._error("room_name is required")

        result = parser.get_room_info(room_name)
        if "error" in result:
            return self._error(result["error"])

        output = [
            f"Room Information: {result['room_name']}",
            "=" * 50,
            "",
            "Formatted View:",
            result['formatted_info'],
            "",
            "Raw Data Available:",
            f"- YY File: {result['yy_path']}",
            f"- Layers: {len(result['data'].get('layers', []))}",
            f"- Room Settings: {'Yes' if result['data'].get('roomSettings') else 'No'}",
        ]
        return [TextContent(type="text", text="\n".join(output))]

    async def _get_object_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        object_name = arguments.get("object_name")
        if not object_name:
            return self._error("object_name is required")

        result = parser.get_object_info(object_name)
        if "error" in result:
            return self._error(result["error"])

        output = [
            f"Object Information: {result['object_name']}",
            "=" * 50,
            "",
            "Formatted View:",
            result['formatted_info'],
            "",
            "Raw Data Available:",
            f"- YY File: {result['yy_path']}",
            f"- Events: {len(result['data'].get('eventList', []))}",
            f"- Physics: {'Enabled' if result['data'].get('physicsObject') else 'Disabled'}",
        ]
        return [TextContent(type="text", text="\n".join(output))]

    async def _get_sprite_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        sprite_name = arguments.get("sprite_name")
        if not sprite_name:
            return self._error("sprite_name is required")

        result = parser.get_sprite_info(sprite_name)
        if "error" in result:
            return self._error(result["error"])

        output = [
            f"Sprite Information: {result['sprite_name']}",
            "=" * 50,
            "",
            f"Sprite Path: {result['sprite_path']}",
            f"YY File: {'Yes' if result['yy_path'] else 'No'}",
            f"Frame Count: {len(result['frames'])}",
        ]

        if result['frames']:
            output.append("")
            output.append("Frames:")
            for i, frame in enumerate(result['frames']):
                output.append(f"  {i+1}. {frame['filename']}")

        return [TextContent(type="text", text="\n".join(output))]

    async def _export_project_data(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        project_path = parser.project_path

        save_to_file = arguments.get("save_to_file", False)
        output_file = arguments.get("output_file")

        export_data = parser.export_all_data()

        if save_to_file:
            if not output_file:
                project_name = os.path.basename(project_path)
                output_file = os.path.join(project_path, f"{project_name}_export.txt")
            else:
                output_file = os.path.abspath(output_file)

            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(export_data)
                return [TextContent(
                    type="text",
                    text=f"Project data exported to: {output_file}\n\nFile size: {len(export_data)} characters"
                )]
            except Exception as e:
                logger.exception("Error saving export file: %s", output_file)
                return self._error(f"Could not save file: {e}")

        return [TextContent(type="text", text=export_data)]

    async def _list_project_assets(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        result = parser.scan_project()

        if "error" in result:
            return self._error(result["error"])

        category_filter = arguments.get("category")
        output = [
            f"Assets in {result['project_name']}:",
            "=" * 50,
        ]

        categories_to_show = [category_filter] if category_filter else list(result['categories'].keys())

        for category in categories_to_show:
            if category in result['categories']:
                info = result['categories'][category]
                if info['assets']:
                    output.append(f"\n{category} ({len(info['assets'])} items):")
                    for asset in info['assets']:
                        gml_files = len(asset['gml_files'])
                        yy_file = "✓" if asset['yy_file'] else "✗"
                        output.append(f"  - {asset['name']} (GML: {gml_files}, YY: {yy_file})")
                        if 0 < gml_files <= 5:
                            for gml in asset['gml_files']:
                                output.append(f"    • {gml['name']}")

        return [TextContent(type="text", text="\n".join(output))]


    async def _search_project(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        query = arguments.get("query")
        if not query:
            return self._error("query is required")

        case_sensitive = arguments.get("case_sensitive", False)
        context_lines = arguments.get("context_lines", 0)
        result = parser.search_in_project(query, case_sensitive=case_sensitive, context_lines=context_lines)

        if "error" in result:
            return self._error(result["error"])

        output = [
            f"Search results for: {result['query']}",
            f"Total matches: {result['total_matches']}",
            "-" * 50,
        ]
        for match in result["matches"]:
            if match["context"]:
                output.extend(match["context"])
                output.append("")  # linha em branco entre matches
            else:
                output.append(f"{match['file']} (line {match['line']}): {match['match']}")
        if not result["matches"]:
            output.append("No matches found.")

        return [TextContent(type="text", text="\n".join(output))]

    async def _get_object_events(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        object_name = arguments.get("object_name")
        if not object_name:
            return self._error("object_name is required")

        result = parser.get_object_events(object_name)
        if "error" in result:
            return self._error(result["error"])

        output = [
            f"Events for object: {result['object_name']}",
            f"Total events: {len(result['events'])}",
            "=" * 50,
        ]
        for event in result["events"]:
            output.append(f"\n[{event['event_subtype']}]  ({event['line_count']} lines)")
            if event["gml_path"]:
                output.append(f"  File: {event['gml_path']}")
            if event["content"] is not None:
                output.append("-" * 40)
                output.append(event["content"])
            else:
                output.append("  (no GML file found)")

        return [TextContent(type="text", text="\n".join(output))]

    async def _get_script_content(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        script_name = arguments.get("script_name")
        if not script_name:
            return self._error("script_name is required")

        result = parser.get_script_content(script_name)
        if "error" in result:
            return self._error(result["error"])

        output = [
            f"Script: {result['script_name']}",
            f"Path: {result['relative_path']}",
            f"Lines: {result['line_count']}",
            "-" * 50,
            result["content"],
        ]
        return [TextContent(type="text", text="\n".join(output))]

    async def _edit_gml_file(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        project_path = parser.project_path

        file_path = arguments.get("file_path")
        new_content = arguments.get("new_content")
        if not file_path:
            return self._error("file_path is required")
        if new_content is None:
            return self._error("new_content is required")

        if not os.path.isabs(file_path):
            file_path = os.path.join(project_path, file_path)

        resolved = os.path.realpath(os.path.abspath(file_path))
        project_real = os.path.realpath(project_path)
        if not (resolved == project_real or resolved.startswith(project_real + os.sep)):
            return self._error("Access denied: file path is outside the project directory")

        create_backup = arguments.get("create_backup", True)
        result = parser.edit_gml_file(file_path, new_content, create_backup=create_backup)

        if "error" in result:
            return self._error(result["error"])

        output = [
            f"File edited successfully: {result['relative_path']}",
            f"Lines written: {result['line_count']}",
            f"Backup saved to: {result['backup_path']}" if result["backup_path"] else "No backup created.",
        ]
        return [TextContent(type="text", text="\n".join(output))]

    async def _find_asset_references(self, arguments: Dict[str, Any]) -> List[TextContent]:
        parser = self._get_parser(arguments)
        asset_name = arguments.get("asset_name")
        if not asset_name:
            return self._error("asset_name is required")

        result = parser.find_asset_references(asset_name)
        if "error" in result:
            return self._error(result["error"])

        output = [
            f"References to asset: {result['asset_name']}",
            f"GML files with references: {result['total_gml_files']}",
            f"Rooms with instances: {result['total_rooms']}",
            "=" * 50,
        ]

        if result["gml_references"]:
            output.append("\nGML References:")
            for ref in result["gml_references"]:
                lines_str = ", ".join(str(ln) for ln in ref["lines"])
                output.append(f"  {ref['file']}  (lines: {lines_str})")
        else:
            output.append("\nNo GML references found.")

        if result["room_instances"]:
            output.append("\nRoom Instances:")
            for ri in result["room_instances"]:
                output.append(f"  {ri['room']}: {ri['instance_count']} instance(s)")
        else:
            output.append("\nNo room instances found.")

        return [TextContent(type="text", text="\n".join(output))]


async def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config_file = os.path.join(os.path.dirname(__file__), 'config.env')
    load_dotenv(config_file)

    arg_parser = argparse.ArgumentParser(description="GameMaker Studio 2 MCP Server")
    arg_parser.add_argument("--project-path", type=str, help="Path to GMS2 project (overrides config.env)")
    args = arg_parser.parse_args()

    project_path = args.project_path or os.getenv('GMS2_PROJECT_PATH')

    if project_path and not os.path.exists(project_path):
        logger.warning("Project path does not exist: %s", project_path)

    mcp_server = GMS2MCPServer(project_path)

    server = Server("gms2-mcp-server")

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        return mcp_server.get_tools()

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        return await mcp_server.handle_tool_call(name, arguments)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error starting MCP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
