"""Tool system initialization and default registry for AI Workspace Assistant."""

from app.agents.tools.specialist_tools import (
    tool_fishing_zone_agent,
    tool_ocean_agent,
    tool_route_agent,
    tool_safety_risk_agent,
    tool_system_health,
    tool_weather_agent,
)
from app.agents.tools.tool_registry import ToolDefinition, ToolRegistry
from app.agents.tools.workspace_tools import (
    tool_apply_file_edit,
    tool_list_project_files,
    tool_propose_file_edit,
    tool_read_project_file,
    tool_run_approved_command,
    tool_run_approved_tests,
)


def create_default_tool_registry() -> ToolRegistry:
    """Build and populate the default tool registry for the workspace assistant."""
    registry = ToolRegistry()

    # Specialist Agent Tools
    registry.register(
        ToolDefinition(
            name="invoke_weather_agent",
            description="Retrieve atmospheric weather telemetry, air temperature, wind speed/direction, and precipitation.",
            category="specialist",
            parameters={
                "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                "location_name": {"type": "string", "description": "Location name label"},
                "forecast_days": {"type": "integer", "description": "Forecast days (1 to 7)"},
            },
            handler=tool_weather_agent,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="invoke_ocean_agent",
            description="Retrieve sea state conditions, wave heights, and WMO Code Table 3700 classifications.",
            category="specialist",
            parameters={
                "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                "location_name": {"type": "string", "description": "Marine location label"},
                "forecast_time_window_hours": {"type": "integer", "description": "Forecast window hours (1 to 168)"},
            },
            handler=tool_ocean_agent,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="invoke_fishing_zone_agent",
            description="Evaluate operational fisheries feasibility while disclosing biological telemetry limitations.",
            category="specialist",
            parameters={
                "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                "location_name": {"type": "string", "description": "Location name label"},
                "forecast_time_window_hours": {"type": "integer", "description": "Forecast window hours"},
                "target_species": {"type": "string", "description": "Target fish species name"},
            },
            handler=tool_fishing_zone_agent,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="invoke_route_agent",
            description="Calculate Great-Circle geodesic distance, initial compass bearings, and estimated transit times.",
            category="specialist",
            parameters={
                "origin_latitude": {"type": "number", "description": "Origin latitude"},
                "origin_longitude": {"type": "number", "description": "Origin longitude"},
                "destination_latitude": {"type": "number", "description": "Destination latitude"},
                "destination_longitude": {"type": "number", "description": "Destination longitude"},
                "origin_name": {"type": "string", "description": "Origin name"},
                "destination_name": {"type": "string", "description": "Destination name"},
                "vessel_speed_knots": {"type": "number", "description": "Cruising speed in knots"},
            },
            handler=tool_route_agent,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="invoke_safety_risk_agent",
            description="Assess marine hazards, gale warnings, sea-state survival limits, and operational risk category.",
            category="specialist",
            parameters={
                "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                "location_name": {"type": "string", "description": "Marine location"},
                "vessel_type": {"type": "string", "description": "Vessel category: small_craft, trawler, cargo"},
                "wave_height_m": {"type": "number", "description": "Observed wave height"},
                "wind_speed_knots": {"type": "number", "description": "Observed wind speed"},
                "precipitation_mm": {"type": "number", "description": "Observed precipitation"},
            },
            handler=tool_safety_risk_agent,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="check_system_health",
            description="Verify active service health, endpoints, and external provider connectivity.",
            category="system",
            parameters={},
            handler=tool_system_health,
            requires_approval=False,
            read_only=True,
        )
    )

    # Workspace & Code Tools
    registry.register(
        ToolDefinition(
            name="read_project_file",
            description="Read the contents of an authorized file within the project workspace.",
            category="workspace",
            parameters={
                "file_path": {"type": "string", "description": "File path relative to workspace root"},
                "start_line": {"type": "integer", "description": "Optional starting line number (1-indexed)"},
                "end_line": {"type": "integer", "description": "Optional ending line number (1-indexed)"},
            },
            handler=tool_read_project_file,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="list_project_files",
            description="List files and directories inside an authorized project directory.",
            category="workspace",
            parameters={
                "directory_path": {"type": "string", "description": "Directory path relative to workspace root"},
            },
            handler=tool_list_project_files,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="propose_file_edit",
            description="Propose a file edit and generate a unified diff without modifying disk.",
            category="workspace",
            parameters={
                "file_path": {"type": "string", "description": "Target file path"},
                "target_content": {"type": "string", "description": "Exact text to replace"},
                "replacement_content": {"type": "string", "description": "Replacement text"},
            },
            handler=tool_propose_file_edit,
            requires_approval=False,
            read_only=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="apply_file_edit",
            description="Apply an authorized change to a file within the project workspace (Requires Approval).",
            category="workspace",
            parameters={
                "file_path": {"type": "string", "description": "Target file path"},
                "target_content": {"type": "string", "description": "Exact text to replace"},
                "replacement_content": {"type": "string", "description": "Replacement text"},
            },
            handler=tool_apply_file_edit,
            requires_approval=True,
            read_only=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="run_approved_tests",
            description="Run authorized test suites (pytest for backend, npm test for frontend) (Requires Approval).",
            category="workspace",
            parameters={
                "test_target": {"type": "string", "description": "'backend', 'frontend', or specific test path"},
            },
            handler=tool_run_approved_tests,
            requires_approval=True,
            read_only=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="run_approved_command",
            description="Run whitelisted development commands like git status or pytest (Requires Approval).",
            category="workspace",
            parameters={
                "command": {"type": "string", "description": "Shell command to run"},
            },
            handler=tool_run_approved_command,
            requires_approval=True,
            read_only=False,
        )
    )

    return registry
