"""Unit tests for independent Route Agent."""

import pytest

from app.agents.route_agent import (
    RouteAgent,
    haversine_distance_km,
    initial_compass_bearing_deg,
    interpolate_points,
)
from app.schemas.agent_schemas import RouteAnalyzeRequest, WaypointItem


def test_haversine_calculation():
    # Mumbai (18.9388, 72.8354) to Goa (15.4989, 73.8278) ~ 400 km
    dist = haversine_distance_km(18.9388, 72.8354, 15.4989, 73.8278)
    assert 380.0 < dist < 420.0


def test_bearing_calculation():
    # Due North: 0 deg
    bearing_n = initial_compass_bearing_deg(10.0, 70.0, 15.0, 70.0)
    assert round(bearing_n, 1) == 0.0

    # Due East: 90 deg
    bearing_e = initial_compass_bearing_deg(0.0, 70.0, 0.0, 75.0)
    assert round(bearing_e, 1) == 90.0


def test_interpolate_points():
    pts = interpolate_points(10.0, 70.0, 15.0, 75.0, num_points=5)
    assert len(pts) == 6
    assert pts[0] == (10.0, 70.0)
    assert pts[-1] == (15.0, 75.0)


@pytest.mark.asyncio
async def test_route_agent_valid_passage():
    agent = RouteAgent()
    request = RouteAnalyzeRequest(
        origin_latitude=18.9388,
        origin_longitude=72.8354,
        origin_name="Mumbai Port",
        destination_latitude=15.4989,
        destination_longitude=73.8278,
        destination_name="Goa Port",
        waypoints=[
            WaypointItem(latitude=17.0, longitude=73.0, name="Ratnagiri Offshore Waypoint")
        ],
        vessel_speed_knots=12.0,
    )

    response = await agent.analyze(request)

    assert response.agent == "Route Agent"
    assert response.status == "success"
    assert response.observations["leg_count"] == 2
    assert response.observations["total_distance_nm"] > 0
    assert response.observations["estimated_transit_time_hours"] > 0
    assert response.analysis["navigation_type"] == "geodesic_straight_line"
    assert response.analysis["is_navigable_channel_verified"] is False
    assert response.observations["is_verified_navigable_route"] is False
    assert response.analysis["route_classification"] == "GEODESIC_STRAIGHT_LINE"
    assert "navigable_route_disclaimer" in response.analysis
    assert "NOT represent a verified navigable maritime route" in response.analysis["navigable_route_disclaimer"]
    assert len(response.warnings) >= 3
    assert "geodesic straight-line distance" in response.warnings[0]



@pytest.mark.asyncio
async def test_route_agent_invalid_coordinates():
    with pytest.raises(Exception):
        RouteAnalyzeRequest(
            origin_latitude=95.0,
            origin_longitude=72.0,
            destination_latitude=15.0,
            destination_longitude=72.0,
        )


@pytest.mark.asyncio
async def test_route_agent_identical_origin_destination():
    agent = RouteAgent()
    request = RouteAnalyzeRequest(
        origin_latitude=15.0,
        origin_longitude=72.0,
        destination_latitude=15.0,
        destination_longitude=72.0,
    )
    response = await agent.analyze(request)

    assert response.status == "success"
    assert response.observations["total_distance_km"] == 0.0
    assert "Origin and destination coordinates are identical" in response.warnings[-1]


@pytest.mark.asyncio
async def test_route_agent_enforces_geodesic_labeling_and_disclaimer():
    """Verify Route Agent explicitly labels output as estimated geodesic distance and retains disclaimers."""
    agent = RouteAgent()
    req = RouteAnalyzeRequest(
        origin_latitude=15.4989,
        origin_longitude=73.8278,
        origin_name="Goa Port",
        destination_latitude=18.9388,
        destination_longitude=72.8354,
        destination_name="Mumbai Port",
        vessel_speed_knots=14.0,
    )
    res = await agent.analyze(req)

    # 1. Calculation method and routing type must be explicitly geodesic
    assert res.data_source["routing_type"] == "straight_line_geodesic"
    assert "Haversine" in res.data_source["calculation_method"]
    assert "without bathymetry, nautical hazards, or land avoidance" in res.data_source["limitations"]

    # 2. Observations must state non-navigable route
    assert res.observations["is_verified_navigable_route"] is False
    assert res.observations["geodesic_distance_km"] > 0
    assert res.analysis["is_navigable_channel_verified"] is False
    assert res.analysis["navigation_type"] == "geodesic_straight_line"
    assert res.analysis["route_classification"] == "GEODESIC_STRAIGHT_LINE"

    # 3. Disclaimers and warnings must explicitly warn against relying on geodesic tracks
    disclaimer = res.analysis["navigable_route_disclaimer"]
    assert "straight-line geodesic (Great-Circle) measurements only" in disclaimer
    assert "does NOT represent a verified navigable maritime route" in disclaimer
    assert "Bathymetric depths, undersea obstructions, shoals" in disclaimer

    # 4. Must not claim the route is safe or navigable
    advisory = res.analysis["advisory"]
    assert "This calculation does not establish vessel safety or channel navigability" in advisory
    assert any("DOES NOT establish that the route is safe or navigable" in w for w in res.warnings)


def test_route_agent_preserves_haversine_formula_math():
    """Verify Haversine formula calculates accurate Great-Circle distances without external engine."""
    # 1 degree of latitude is ~111.19 km
    d_1deg = haversine_distance_km(0.0, 0.0, 1.0, 0.0)
    assert 111.0 < d_1deg < 111.5

    # Known distance: Goa to Mumbai ~ 400 km
    d_goa_mumbai = haversine_distance_km(15.4989, 73.8278, 18.9388, 72.8354)
    assert 390.0 < d_goa_mumbai < 410.0


@pytest.mark.asyncio
async def test_route_agent_goa_to_mumbai_propagation_and_transit():
    """Regression Test: Route Agent calculates distinct endpoints, ~446 km distance, and positive transit hours."""
    agent = RouteAgent()
    req = RouteAnalyzeRequest(
        origin_latitude=15.0,
        origin_longitude=72.0,
        origin_name="Goa Sector",
        destination_latitude=18.95,
        destination_longitude=72.82,
        destination_name="Mumbai Port",
        vessel_speed_knots=12.0,
    )
    res = await agent.analyze(req)

    assert res.status == "success"
    # Separate endpoints must be preserved in location
    assert res.location["origin"]["name"] == "Goa Sector"
    assert res.location["origin"]["latitude"] == 15.0
    assert res.location["origin"]["longitude"] == 72.0
    assert res.location["destination"]["name"] == "Mumbai Port"
    assert res.location["destination"]["latitude"] == 18.95
    assert res.location["destination"]["longitude"] == 72.82

    # Geodesic distance must be calculated from actual endpoints (~446 km)
    dist_km = res.observations["total_distance_km"]
    assert 430.0 < dist_km < 460.0
    assert res.observations["estimated_transit_time_hours"] > 15.0


