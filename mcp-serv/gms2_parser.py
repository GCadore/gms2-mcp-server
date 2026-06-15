"""
GameMaker Studio 2 Project Parser Module
"""

import json
import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GMS2ProjectParser:
    """Parser for GameMaker Studio 2 projects."""

    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self._gml_files: List[Tuple[str, str, str, Optional[str]]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_asset_name(self, name: str) -> bool:
        """Returns True only when the name contains safe identifier characters."""
        return bool(re.match(r'^[a-zA-Z0-9_\-]+$', name))

    def _load_yy_file(self, path: str) -> Dict[str, Any]:
        """Loads and parses a .yy file, tolerating GMS2 trailing-comma quirks."""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        cleaned = re.sub(r",\s*([}\]])", r"\1", content)
        return json.loads(cleaned)

    def _is_within_project(self, path: str) -> bool:
        """Returns True when the resolved path stays inside the project tree."""
        resolved = os.path.realpath(os.path.abspath(path))
        project_real = os.path.realpath(self.project_path)
        return resolved == project_real or resolved.startswith(project_real + os.sep)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_project(self) -> Dict[str, Any]:
        """Scans the project and returns its file structure."""
        if not os.path.exists(self.project_path):
            return {"error": f"Project path not found: {self.project_path}"}

        yyp_files = [f for f in os.listdir(self.project_path) if f.endswith('.yyp')]
        if not yyp_files:
            return {"error": f"No .yyp file found in {self.project_path}"}

        self._gml_files.clear()

        asset_categories = {
            "Objects": "objects",
            "Scripts": "scripts",
            "Rooms": "rooms",
            "Sprites": "sprites",
            "Notes": "notes",
            "Tile Sets": "tilesets",
            "Timelines": "timelines",
            "Fonts": "fonts",
            "Sounds": "sounds",
            "Extensions": "extensions",
        }

        structure: Dict[str, Any] = {
            "project_name": os.path.basename(self.project_path),
            "project_path": self.project_path,
            "categories": {},
            "gml_files": [],
            "total_gml_files": 0,
        }

        for display_name, folder_name in asset_categories.items():
            category_path = os.path.join(self.project_path, folder_name)
            if os.path.isdir(category_path):
                structure["categories"][display_name] = self._scan_category(category_path, display_name)

        self._scan_gml_files()
        structure["gml_files"] = self._gml_files
        structure["total_gml_files"] = len(self._gml_files)

        return structure

    def _scan_category(self, category_path: str, category_name: str) -> Dict[str, Any]:
        """Scans an asset category folder."""
        category_info: Dict[str, Any] = {"path": category_path, "assets": []}

        try:
            for asset_name in sorted(os.listdir(category_path)):
                asset_path = os.path.join(category_path, asset_name)
                if not os.path.isdir(asset_path):
                    continue

                asset_info: Dict[str, Any] = {
                    "name": asset_name,
                    "path": asset_path,
                    "type": category_name.lower().rstrip('s'),
                    "yy_file": None,
                    "gml_files": [],
                }

                yy_path = os.path.join(asset_path, f"{asset_name}.yy")
                if os.path.isfile(yy_path):
                    asset_info["yy_file"] = yy_path

                for file in os.listdir(asset_path):
                    if file.endswith('.gml'):
                        asset_info["gml_files"].append({
                            "name": file,
                            "path": os.path.join(asset_path, file),
                        })

                category_info["assets"].append(asset_info)

        except OSError as e:
            category_info["error"] = f"Could not read directory: {e}"

        return category_info

    def _scan_gml_files(self) -> None:
        """Walks the project tree and collects all .gml file entries."""
        # Not part of the GMS2 asset tree — skip entirely
        _SKIP_DIRS = {'options', 'datafiles', 'configs', '.git', '.vscode', 'temp'}

        for root, dirs, files in os.walk(self.project_path):
            relative_root = os.path.relpath(root, self.project_path)
            if relative_root != '.':
                parts = relative_root.split(os.sep)
                if parts and parts[0].lower() in _SKIP_DIRS:
                    dirs[:] = []
                    continue

            for file in sorted(files):
                if not file.endswith('.gml'):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.project_path)
                parent_dir = os.path.dirname(file_path)
                asset_name = os.path.basename(parent_dir)

                asset_yy_path: Optional[str] = None
                potential_yy = os.path.join(parent_dir, f"{asset_name}.yy")
                if os.path.isfile(potential_yy):
                    asset_yy_path = potential_yy

                display_name = f"{asset_name} / {os.path.splitext(file)[0]}"
                self._gml_files.append((display_name, file_path, relative_path, asset_yy_path))

    def get_gml_content(self, file_path: str) -> Dict[str, Any]:
        """Returns the content of a .gml file, enforcing project-boundary checks."""
        if not self._is_within_project(file_path):
            return {"error": "Access denied: file path is outside the project directory"}

        try:
            if not os.path.isfile(file_path):
                return {"error": f"File not found: {file_path}"}

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "file_path": file_path,
                "relative_path": os.path.relpath(file_path, self.project_path),
                "content": content,
                "line_count": len(content.splitlines()),
            }
        except Exception as e:
            logger.exception("Error reading GML file: %s", file_path)
            return {"error": f"Error reading file: {e}"}

    def get_room_info(self, room_name: str) -> Dict[str, Any]:
        """Returns parsed information for a room asset."""
        if not self._validate_asset_name(room_name):
            return {"error": f"Invalid room name: '{room_name}'"}

        room_path = os.path.join(self.project_path, "rooms", room_name)
        room_yy_path = os.path.join(room_path, f"{room_name}.yy")

        if not os.path.isfile(room_yy_path):
            return {"error": f"Room not found: {room_name}"}

        try:
            room_data = self._load_yy_file(room_yy_path)
            return {
                "room_name": room_name,
                "room_path": room_path,
                "yy_path": room_yy_path,
                "data": room_data,
                "formatted_info": self._format_room_data(room_data),
            }
        except json.JSONDecodeError as e:
            return {"error": f"Error parsing room JSON: {e}"}
        except Exception as e:
            logger.exception("Error reading room '%s'", room_name)
            return {"error": f"Error reading room file: {e}"}

    def get_object_info(self, object_name: str) -> Dict[str, Any]:
        """Returns parsed information for an object asset."""
        if not self._validate_asset_name(object_name):
            return {"error": f"Invalid object name: '{object_name}'"}

        object_path = os.path.join(self.project_path, "objects", object_name)
        object_yy_path = os.path.join(object_path, f"{object_name}.yy")

        if not os.path.isfile(object_yy_path):
            return {"error": f"Object not found: {object_name}"}

        try:
            object_data = self._load_yy_file(object_yy_path)
            return {
                "object_name": object_name,
                "object_path": object_path,
                "yy_path": object_yy_path,
                "data": object_data,
                "formatted_info": self._format_object_data(object_data),
            }
        except json.JSONDecodeError as e:
            return {"error": f"Error parsing object JSON: {e}"}
        except Exception as e:
            logger.exception("Error reading object '%s'", object_name)
            return {"error": f"Error reading object file: {e}"}

    def get_sprite_info(self, sprite_name: str) -> Dict[str, Any]:
        """Returns information about a sprite asset."""
        if not self._validate_asset_name(sprite_name):
            return {"error": f"Invalid sprite name: '{sprite_name}'"}

        sprite_path = os.path.join(self.project_path, "sprites", sprite_name)
        sprite_yy_path = os.path.join(sprite_path, f"{sprite_name}.yy")

        if not os.path.isdir(sprite_path):
            return {"error": f"Sprite not found: {sprite_name}"}

        sprite_info: Dict[str, Any] = {
            "sprite_name": sprite_name,
            "sprite_path": sprite_path,
            "yy_path": sprite_yy_path if os.path.isfile(sprite_yy_path) else None,
            "frames": [],
        }

        try:
            for filename in sorted(os.listdir(sprite_path)):
                if filename.lower().endswith('.png'):
                    sprite_info["frames"].append({
                        "filename": filename,
                        "path": os.path.join(sprite_path, filename),
                    })
        except OSError as e:
            sprite_info["error"] = f"Error reading sprite folder: {e}"

        return sprite_info

    def export_all_data(self) -> str:
        """Exports all project data as a single text document."""
        if not self._gml_files:
            self.scan_project()

        output_lines = [
            f"// GML and YY Data Export from Project: {self.project_path}",
            f"// Total GML Files Found: {len(self._gml_files)}",
            "=" * 70,
            "",
        ]

        exported_yy_files: set = set()

        for display_name, file_path, relative_path, asset_yy_path in self._gml_files:
            output_lines.append(f"// ----- Start GML: {display_name} -----")
            output_lines.append(f"// ----- GML Path: {relative_path} -----")
            output_lines.append("")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    output_lines.append(f.read())
            except Exception:
                logger.exception("Error reading GML file during export: %s", relative_path)
                output_lines.append(f"// ***** ERROR READING GML FILE: {relative_path} *****")

            output_lines.append("")
            output_lines.append("-" * 50 + "[End GML]" + "-" * 19)
            output_lines.append("")

            if asset_yy_path and os.path.isfile(asset_yy_path) and asset_yy_path not in exported_yy_files:
                relative_yy_path = os.path.relpath(asset_yy_path, self.project_path)
                asset_name = os.path.basename(os.path.dirname(asset_yy_path))

                output_lines.append(f"// ----- Associated YY File: {asset_name} -----")
                output_lines.append(f"// ----- YY Path: {relative_yy_path} -----")
                output_lines.append("")

                try:
                    with open(asset_yy_path, 'r', encoding='utf-8') as f:
                        output_lines.append(f.read())
                except Exception:
                    logger.exception("Error reading YY file during export: %s", relative_yy_path)
                    output_lines.append(f"// ***** ERROR READING YY FILE: {relative_yy_path} *****")

                output_lines.append("")
                output_lines.append("=" * 30 + "[End YY]" + "=" * 32)
                output_lines.append("")

                exported_yy_files.add(asset_yy_path)

        return "\n".join(output_lines)

    def search_in_project(self, query: str, case_sensitive: bool = False, context_lines: int = 0) -> Dict[str, Any]:
        """Searches for text or regex across all GML files in the project."""
        if not self._gml_files:
            scan_result = self.scan_project()
            if "error" in scan_result:
                return scan_result

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}

        matches: List[Dict[str, Any]] = []
        total_matches = 0
        MAX_MATCHES = 200

        for display_name, file_path, relative_path, _ in self._gml_files:
            if total_matches >= MAX_MATCHES:
                break
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception:
                logger.exception("Error reading GML file during search: %s", file_path)
                continue

            for line_num, line in enumerate(lines, start=1):
                if total_matches >= MAX_MATCHES:
                    break
                m = pattern.search(line)
                if m:
                    context: List[str] = []
                    if context_lines > 0:
                        before = lines[max(0, line_num - 1 - context_lines) : line_num - 1]
                        after = lines[line_num : min(len(lines), line_num + context_lines)]
                        for ctx_line in before:
                            context.append("  " + ctx_line.rstrip("\n"))
                        context.append("> " + line.rstrip("\n"))
                        for ctx_line in after:
                            context.append("  " + ctx_line.rstrip("\n"))
                    matches.append({
                        "file": display_name,
                        "relative_path": relative_path,
                        "line": line_num,
                        "column": m.start() + 1,
                        "match": line.rstrip("\n"),
                        "context": context,
                    })
                    total_matches += 1

        return {"query": query, "total_matches": total_matches, "matches": matches}

    def get_object_events(self, object_name: str) -> Dict[str, Any]:
        """Returns all events of an object with the GML code for each one."""
        if not self._validate_asset_name(object_name):
            return {"error": f"Invalid object name: '{object_name}'"}

        object_path = os.path.join(self.project_path, "objects", object_name)
        object_yy_path = os.path.join(object_path, f"{object_name}.yy")

        if not os.path.isfile(object_yy_path):
            return {"error": f"Object not found: {object_name}"}

        EVENT_TYPES: Dict[int, str] = {
            0: "Create", 1: "Destroy", 2: "Alarm", 3: "Step",
            4: "Collision", 5: "Keyboard", 6: "Mouse", 7: "Other",
            8: "Draw", 9: "KeyPress", 10: "KeyRelease", 13: "CleanUp",
        }
        STEP_SUBTYPES: Dict[int, str] = {0: "Step", 1: "Begin_Step", 2: "End_Step"}
        DRAW_SUBTYPES: Dict[int, str] = {
            0: "Draw", 64: "Draw_GUI", 72: "Draw_GUI_Begin",
            73: "Draw_GUI_End", 76: "Pre-Draw", 77: "Post-Draw",
        }

        try:
            object_data = self._load_yy_file(object_yy_path)
        except json.JSONDecodeError as e:
            return {"error": f"Error parsing object JSON: {e}"}
        except Exception as e:
            logger.exception("Error reading object '%s'", object_name)
            return {"error": f"Error reading object file: {e}"}

        events: List[Dict[str, Any]] = []
        for event in object_data.get("eventList", []):
            etype = event.get("eventtype", event.get("evType", -1))
            enumb = event.get("enumb", event.get("evNum", 0))
            type_name = EVENT_TYPES.get(etype, f"Event{etype}")

            if etype == 3:
                event_label = STEP_SUBTYPES.get(enumb, f"Step_{enumb}")
            elif etype == 8:
                event_label = DRAW_SUBTYPES.get(enumb, f"Draw_{enumb}")
            elif etype == 2:
                event_label = f"Alarm_{enumb}"
            elif enumb > 0:
                event_label = f"{type_name}_{enumb}"
            else:
                event_label = type_name

            gml_path = os.path.join(object_path, f"{event_label}.gml")
            content: Optional[str] = None
            line_count = 0
            if os.path.isfile(gml_path):
                try:
                    with open(gml_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    line_count = len(content.splitlines())
                except Exception:
                    logger.exception("Error reading event GML: %s", gml_path)

            events.append({
                "event_type": type_name,
                "event_subtype": event_label,
                "event_num": enumb,
                "gml_path": os.path.relpath(gml_path, self.project_path) if os.path.isfile(gml_path) else None,
                "content": content,
                "line_count": line_count,
            })

        return {"object_name": object_name, "events": events}

    def get_script_content(self, script_name: str) -> Dict[str, Any]:
        """Returns the GML content of a script asset by name."""
        if not self._validate_asset_name(script_name):
            return {"error": f"Invalid script name: '{script_name}'"}

        script_path = os.path.join(self.project_path, "scripts", script_name, f"{script_name}.gml")

        if not os.path.isfile(script_path):
            return {"error": f"Script not found: {script_name}"}

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "script_name": script_name,
                "file_path": script_path,
                "relative_path": os.path.relpath(script_path, self.project_path),
                "content": content,
                "line_count": len(content.splitlines()),
            }
        except Exception as e:
            logger.exception("Error reading script '%s'", script_name)
            return {"error": f"Error reading script file: {e}"}

    def edit_gml_file(self, file_path: str, new_content: str, create_backup: bool = True) -> Dict[str, Any]:
        """Overwrites the content of an existing GML file."""
        if not self._is_within_project(file_path):
            return {"error": "Access denied: file path is outside the project directory"}

        if not file_path.endswith('.gml'):
            return {"error": "Only .gml files can be edited"}

        if not os.path.isfile(file_path):
            return {"error": f"File not found: {file_path}"}

        backup_path: Optional[str] = None
        if create_backup:
            backup_path = file_path + ".bak"
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original)
            except Exception as e:
                logger.exception("Error creating backup for: %s", file_path)
                return {"error": f"Could not create backup: {e}"}

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            self._gml_files.clear()
        except Exception as e:
            logger.exception("Error writing GML file: %s", file_path)
            return {"error": f"Error writing file: {e}"}

        return {
            "file_path": file_path,
            "relative_path": os.path.relpath(file_path, self.project_path),
            "line_count": len(new_content.splitlines()),
            "backup_path": backup_path,
        }

    def find_asset_references(self, asset_name: str) -> Dict[str, Any]:
        """Finds all references to an asset (object, script, sprite) across the project."""
        if not self._gml_files:
            scan_result = self.scan_project()
            if "error" in scan_result:
                return scan_result

        pattern = re.compile(r'\b' + re.escape(asset_name) + r'\b')

        gml_refs: List[Dict[str, Any]] = []
        for display_name, file_path, relative_path, _ in self._gml_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception:
                logger.exception("Error reading GML file during reference search: %s", file_path)
                continue

            hit_lines = [
                line_num for line_num, line in enumerate(lines, start=1)
                if pattern.search(line)
            ]
            if hit_lines:
                gml_refs.append({
                    "file": display_name,
                    "relative_path": relative_path,
                    "lines": hit_lines,
                })

        room_instances: List[Dict[str, Any]] = []
        rooms_path = os.path.join(self.project_path, "rooms")
        if os.path.isdir(rooms_path):
            for room_name in sorted(os.listdir(rooms_path)):
                room_dir = os.path.join(rooms_path, room_name)
                room_yy = os.path.join(room_dir, f"{room_name}.yy")
                if not os.path.isdir(room_dir) or not os.path.isfile(room_yy):
                    continue
                try:
                    room_data = self._load_yy_file(room_yy)
                except Exception:
                    logger.exception("Error parsing room YY for references: %s", room_yy)
                    continue

                count = sum(
                    1
                    for layer in room_data.get("layers", [])
                    for inst in layer.get("instances", [])
                    if isinstance(inst.get("objId"), dict) and inst["objId"].get("name") == asset_name
                )
                if count > 0:
                    room_instances.append({"room": room_name, "instance_count": count})

        return {
            "asset_name": asset_name,
            "gml_references": gml_refs,
            "room_instances": room_instances,
            "total_gml_files": len(gml_refs),
            "total_rooms": len(room_instances),
        }

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_room_data(self, data: Dict[str, Any]) -> str:
        """Renders room data as an indented tree."""
        output_lines = [data.get('name', 'Unknown Room')]

        layers = data.get('layers', [])
        has_more = data.get('roomSettings') or data.get('isPersistent') is not None
        output_lines.append(f"{'├──' if has_more else '└──'} Layers ({len(layers)})")

        for i, layer in enumerate(layers):
            is_last_layer = i == len(layers) - 1
            layer_connector = "│   " if not is_last_layer else "    "
            layer_prefix = f"{layer_connector}{'└──' if is_last_layer else '├──'}"

            layer_name = layer.get('name', f'Unnamed Layer {i}')
            layer_type = layer.get('__type', layer.get('modelName', 'Unknown'))
            output_lines.append(f"{layer_prefix} {layer_name} [{layer_type.replace('GM', '')}]")

            if layer_type == "GMInstanceLayer":
                instances = layer.get('instances', [])
                inst_connector = f"{layer_connector}    "
                inst_prefix = f"{inst_connector}└──"

                if instances:
                    output_lines.append(f"{inst_prefix} Instances ({len(instances)})")
                    counts = Counter(
                        inst.get('objId', {}).get('name', 'UnknownObject')
                        for inst in instances
                    )
                    obj_connector = f"{inst_connector}    "
                    sorted_items = sorted(counts.items())
                    for j, (obj_name, count) in enumerate(sorted_items):
                        is_last_obj = j == len(sorted_items) - 1
                        obj_prefix = f"{obj_connector}{'└──' if is_last_obj else '├──'}"
                        count_str = f" (x{count})" if count > 1 else ""
                        output_lines.append(f"{obj_prefix} {obj_name}{count_str}")

        room_settings = data.get('roomSettings', {})
        if room_settings:
            output_lines.append("└── Properties")
            prop_items = [
                f"Width: {room_settings.get('Width', '?')}",
                f"Height: {room_settings.get('Height', '?')}",
                f"Speed: {room_settings.get('Speed', 30)}",
                f"Persistent: {data.get('isPersistent', False)}",
            ]
            creation_code = data.get('creationCodeFile', '')
            if creation_code:
                prop_items.append(f"Creation Code: {os.path.basename(creation_code)}")

            for k, prop_text in enumerate(prop_items):
                is_last = k == len(prop_items) - 1
                prop_prefix = f"    {'└──' if is_last else '├──'}"
                output_lines.append(f"{prop_prefix} {prop_text}")

        return "\n".join(output_lines)

    def _format_object_data(self, data: Dict[str, Any]) -> str:
        """Renders object data as a structured text report."""
        obj_name = data.get('name', 'Unknown Object')
        output_lines = [
            f"Object: {obj_name}",
            "=" * (len(obj_name) + 8),
            "",
            "[Properties]",
        ]

        sprite_id = data.get('spriteId')
        output_lines.append(f"  Sprite: {sprite_id.get('name', 'None') if sprite_id else 'None'}")

        mask_id = data.get('spriteMaskId')
        output_lines.append(f"  Mask: {mask_id.get('name', 'Same as Sprite') if mask_id else 'Same as Sprite'}")

        parent_id = data.get('parentObjectId')
        output_lines.append(f"  Parent: {parent_id.get('name', 'None') if parent_id else 'None'}")

        output_lines.extend([
            f"  Visible: {data.get('visible', True)}",
            f"  Solid: {data.get('solid', False)}",
            f"  Persistent: {data.get('persistent', False)}",
            "",
            f"[Events ({len(data.get('eventList', []))})]",
            "",
        ])

        if data.get('physicsObject', False):
            output_lines.extend([
                "[Physics Properties]",
                "  Enabled: True",
                f"  Sensor: {data.get('physicsSensor', False)}",
                f"  Shape: {data.get('physicsShape', 1)}",
                f"  Density: {data.get('physicsDensity', 0.5)}",
                f"  Restitution: {data.get('physicsRestitution', 0.1)}",
                f"  Group: {data.get('physicsGroup', 1)}",
                f"  Linear Damping: {data.get('physicsLinearDamping', 0.1)}",
                f"  Angular Damping: {data.get('physicsAngularDamping', 0.1)}",
                f"  Friction: {data.get('physicsFriction', 0.2)}",
                f"  Awake: {data.get('physicsStartAwake', True)}",
                f"  Kinematic: {data.get('physicsKinematic', False)}",
            ])
        else:
            output_lines.extend(["[Physics Properties]", "  Enabled: False"])

        obj_props = data.get('properties', [])
        output_lines.extend(["", f"[Object Variables ({len(obj_props)})]"])
        if obj_props:
            for prop in obj_props:
                prop_name = prop.get('name', prop.get('varName', 'UnknownVar'))
                prop_val = prop.get('value', prop.get('varValue', 'UnknownVal'))
                prop_type = prop.get('type', prop.get('varType', '?'))
                output_lines.append(f"  - {prop_name} = {prop_val} (Type: {prop_type})")
        else:
            output_lines.append("  (None)")

        return "\n".join(output_lines)
