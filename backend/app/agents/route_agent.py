"""Route Agent for ORCA Marine Intelligence.

An independent AI agent that calculates maritime geodesic distance, leg bearings,
waypoint geometry, and transit estimations. Explicitly distinguishes straight-line
geodesic calculation from an authorized navigable channel and enforces maritime navigation warnings.
"""

from datetime import datetime, timezone
import math
from typing import Any

from app.schemas.agent_schemas import (
    RouteAnalyzeRequest,
    RouteAnalyzeResponse,
    RouteGeometryPoint,
    RouteLeg,
)

EARTH_RADIUS_KM = 6371.0
KM_PER_NAUTICAL_MILE = 1.852


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the Great-Circle distance between two points on a sphere in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def initial_compass_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the initial compass bearing from point 1 to point 2 in degrees (0..360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    initial_bearing = math.atan2(y, x)
    return (math.degrees(initial_bearing) + 360.0) % 360.0


def interpolate_points(
    lat1: float, lon1: float, lat2: float, lon2: float, num_points: int = 5
) -> list[tuple[float, float]]:
    """Interpolate points between two coordinates for route geometry rendering."""
    points = []
    for i in range(num_points + 1):
        fraction = i / float(num_points)
        lat = lat1 + fraction * (lat2 - lat1)
        lon = lon1 + fraction * (lon2 - lon1)
        points.append((round(lat, 5), round(lon, 5)))
    return points


class RouteAgent:
    """Independent Route Agent."""

    async def analyze(self, request: RouteAnalyzeRequest) -> RouteAnalyzeResponse:
        """Calculate route distances, legs, and geometry."""
        # 1. Validate coordinates
        points_to_check = [
            ("origin", request.origin_latitude, request.origin_longitude),
            ("destination", request.destination_latitude, request.destination_longitude),
        ]
        for idx, wp in enumerate(request.waypoints):
            points_to_check.append((f"waypoint_{idx + 1}", wp.latitude, wp.longitude))

        for name, lat, lon in points_to_check:
            if not -90.0 <= lat <= 90.0:
                raise ValueError(f"Invalid latitude for {name}: {lat}")
            if not -180.0 <= lon <= 180.0:
                raise ValueError(f"Invalid longitude for {name}: {lon}")

        # 2. Build route nodes: Origin -> Waypoints -> Destination
        route_nodes = [
            (request.origin_name or "Origin", request.origin_latitude, request.origin_longitude)
        ]
        for wp in request.waypoints:
            route_nodes.append((wp.name or "Waypoint", wp.latitude, wp.longitude))
        route_nodes.append(
            (request.destination_name or "Destination", request.destination_latitude, request.destination_longitude)
        )

        # 3. Calculate legs and geometry
        legs: list[RouteLeg] = []
        geometry: list[RouteGeometryPoint] = []
        total_km = 0.0

        for i in range(len(route_nodes) - 1):
            from_name, f_lat, f_lon = route_nodes[i]
            to_name, t_lat, t_lon = route_nodes[i + 1]

            d_km = haversine_distance_km(f_lat, f_lon, t_lat, t_lon)
            d_nm = d_km / KM_PER_NAUTICAL_MILE
            bearing = initial_compass_bearing_deg(f_lat, f_lon, t_lat, t_lon)
            total_km += d_km

            legs.append(
                RouteLeg(
                    from_name=from_name,
                    to_name=to_name,
                    from_lat=f_lat,
                    from_lon=f_lon,
                    to_lat=t_lat,
                    to_lon=t_lon,
                    distance_km=round(d_km, 2),
                    distance_nm=round(d_nm, 2),
                    initial_bearing_deg=round(bearing, 1),
                )
            )

            # Generate geometry points
            interp = interpolate_points(f_lat, f_lon, t_lat, t_lon, num_points=5)
            for lat, lon in interp:
                geometry.append(RouteGeometryPoint(latitude=lat, longitude=lon, leg_index=i))

        total_nm = total_km / KM_PER_NAUTICAL_MILE
        speed = request.vessel_speed_knots
        transit_hours = total_nm / speed if speed > 0 else 0.0

        warnings = [
            "CRITICAL NOTICE: Route calculation is based on geodesic straight-line distance.",
            "DOES NOT verify bathymetric water depth, shoals, reef hazards, or landmass occlusion.",
            "DOES NOT replace Electronic Navigational Charts (ENC) or official Hydrographic Voyage Plans.",
            "DOES NOT establish that the route is safe or navigable without appropriate supporting navigation data.",
        ]

        if total_km == 0.0:
            warnings.append("Origin and destination coordinates are identical.")

        summary = (
            f"Estimated geodesic voyage from '{request.origin_name}' to '{request.destination_name}' "
            f"via {len(request.waypoints)} intermediate waypoints: Total estimated geodesic distance is "
            f"{round(total_nm, 1)} NM ({round(total_km, 1)} km) across {len(legs)} legs. "
            f"Estimated transit time at {speed:.1f} knots is approximately {round(transit_hours, 1)} hours. "
            f"Straight-line geodesic estimate only; does NOT account for bathymetry, nautical hazards, or navigable channels."
        )

        return RouteAnalyzeResponse(
            status="success",
            location={
                "origin": {
                    "name": request.origin_name,
                    "latitude": request.origin_latitude,
                    "longitude": request.origin_longitude,
                },
                "destination": {
                    "name": request.destination_name,
                    "latitude": request.destination_latitude,
                    "longitude": request.destination_longitude,
                },
                "waypoints_count": len(request.waypoints),
            },
            data_source={
                "calculation_method": "Great-Circle Geodesic (Haversine Formula)",
                "routing_type": "straight_line_geodesic",
                "limitations": "Geodesic calculation without bathymetry, nautical hazards, or land avoidance. Does not verify route safety or navigability.",
            },
            observations={
                "total_distance_km": round(total_km, 2),
                "total_distance_nm": round(total_nm, 2),
                "geodesic_distance_km": round(total_km, 2),
                "geodesic_distance_nm": round(total_nm, 2),
                "is_verified_navigable_route": False,
                "vessel_speed_knots": speed,
                "estimated_transit_time_hours": round(transit_hours, 2),
                "leg_count": len(legs),
            },
            analysis={
                "summary": summary,
                "navigation_type": "geodesic_straight_line",
                "route_classification": "GEODESIC_STRAIGHT_LINE",
                "is_verified_navigable_route": False,
                "is_navigable_channel_verified": False,
                "navigable_route_disclaimer": (
                    "CRITICAL NOTICE: Calculated distances represent straight-line geodesic (Great-Circle) measurements only. "
                    "This does NOT represent a verified navigable maritime route. "
                    "Bathymetric depths, undersea obstructions, shoals, islands, and Maritime Traffic Separation Schemes (TSS) "
                    "are unverified. Mariners must consult authorized nautical charts (ENC/Admiralty) before navigation."
                ),
                "legs": [leg.model_dump() for leg in legs],
                "geometry_points_count": len(geometry),
                "geometry": [pt.model_dump() for pt in geometry],
                "advisory": (
                    "Use this calculation for rough passage planning only. "
                    "This calculation does not establish vessel safety or channel navigability. "
                    "Vessel masters must verify safe water depths, TSS corridors, "
                    "and local aids to navigation on authorized nautical charts."
                ),
            },
            warnings=warnings,
        )
