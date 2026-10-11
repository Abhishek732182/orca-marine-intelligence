"""Tests for ORCA Marine Intelligence Agent workflow and API endpoint."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents import marine_graph as workflow
from app.agents.marine_graph import MarineState
from app.agents.sea_state_rules import classify_sea_state
from app.main import app
from app.schemas.evidence import EvidenceRecord

from datetime import datetime, timedelta, timezone

client = TestClient(app)


def test_existing_endpoints_preserved():
    """Verify existing health and marine endpoints are untouched."""
    res_health_root = client.get("/health")
    assert res_health_root.status_code == 200
    assert res_health_root.json()["status"] == "ok"

    res_health_api = client.get("/api/health")
    assert res_health_api.status_code == 200
    assert res_health_api.json()["status"] == "ok"


def test_orca_analyze_endpoint_success(monkeypatch):
    """Test POST /api/orca/analyze returns complete structured JSON."""
    now_utc = datetime.now(timezone.utc)

    async def fake_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id="ev-001",
                source="open-meteo-marine",
                source_record_id=f"2026-10-10T12:00:{latitude}:{longitude}",
                variable="wave_height",
                value=1.8,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc),
                retrieved_at=now_utc,
                status="valid",
                quality_flags=["forecast_data"],
            ),
            EvidenceRecord(
                evidence_id="ev-002",
                source="open-meteo-marine",
                source_record_id=f"2026-10-10T13:00:{latitude}:{longitude}",
                variable="wave_height",
                value=2.1,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 10, 13, 0, 0, tzinfo=timezone.utc),
                retrieved_at=now_utc,
                status="valid",
                quality_flags=["forecast_data"],
            ),
        ]

    monkeypatch.setattr(workflow.provider, "fetch", fake_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={
            "location_name": "Arabian Sea Offshore Test",
            "latitude": 15.0,
            "longitude": 72.0,
            "forecast_time_window_hours": 24,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["agent_name"] == "ORCA Marine Intelligence Agent"
    assert data["status"] == "valid"
    assert data["location"]["location_name"] == "Arabian Sea Offshore Test"
    assert data["location"]["requested_latitude"] == 15.0
    assert data["location"]["requested_longitude"] == 72.0

    # Measurements validation
    measurements = data["measurements"]
    assert measurements["sample_count"] == 2
    assert measurements["min_wave_height_m"] == 1.8
    assert measurements["max_wave_height_m"] == 2.1
    assert measurements["avg_wave_height_m"] == 1.95
    assert measurements["unit"] == "m"

    # WMO Classification validation (2.1m is Moderate, WMO Code 4)
    analysis = data["analysis"]
    assert analysis["sea_state_code"] == 4
    assert analysis["sea_state_category"] == "Moderate"
    assert "WMO Code Table 3700" in analysis["rule_standard"]
    assert "not constitute a maritime navigation or fishing safety clearance" in analysis["advisory"]

    # Limitations check
    assert len(data["limitations"]) >= 3
    assert any("fishing" in lim.lower() for lim in data["limitations"])

    # Step progress tracking
    assert len(data["step_progress"]) == 5


def test_orca_analyze_endpoint_rejects_invalid_coordinates():
    """Verify endpoint rejects invalid coordinates with 422."""
    # Latitude > 90
    resp_lat = client.post(
        "/api/orca/analyze",
        json={
            "location_name": "Invalid Lat",
            "latitude": 95.0,
            "longitude": 72.0,
        },
    )
    assert resp_lat.status_code == 422

    # Longitude > 180
    resp_lon = client.post(
        "/api/orca/analyze",
        json={
            "location_name": "Invalid Lon",
            "latitude": 15.0,
            "longitude": 200.0,
        },
    )
    assert resp_lon.status_code == 422

    # Negative forecast time window
    resp_window = client.post(
        "/api/orca/analyze",
        json={
            "location_name": "Invalid Window",
            "latitude": 15.0,
            "longitude": 72.0,
            "forecast_time_window_hours": 0,
        },
    )
    assert resp_window.status_code == 422


def test_orca_analyze_endpoint_handles_missing_evidence(monkeypatch):
    """Test endpoint response when provider returns 0 records (e.g. land coordinates)."""
    async def empty_fetch(*, latitude, longitude):
        return []

    monkeypatch.setattr(workflow.provider, "fetch", empty_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={
            "location_name": "Inland Land Point",
            "latitude": 21.14,
            "longitude": 79.08,
            "forecast_time_window_hours": 24,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "insufficient_evidence"
    assert data["measurements"]["sample_count"] == 0
    assert data["measurements"]["min_wave_height_m"] is None
    assert data["analysis"]["sea_state_category"] == "UNKNOWN"
    assert data["analysis"]["sea_state_code"] is None
    assert "UNKNOWN / INCOMPLETE" in data["analysis"]["advisory"]


def test_wmo_sea_state_rules():
    """Verify WMO Code Table 3700 classification thresholds."""
    assert classify_sea_state(0.0)["category"] == "Calm (glassy)"
    assert classify_sea_state(0.0)["wmo_code"] == 0

    assert classify_sea_state(0.05)["category"] == "Calm (rippled)"
    assert classify_sea_state(0.05)["wmo_code"] == 1

    assert classify_sea_state(0.3)["category"] == "Smooth"
    assert classify_sea_state(0.3)["wmo_code"] == 2

    assert classify_sea_state(0.94)["category"] == "Slight"
    assert classify_sea_state(0.94)["wmo_code"] == 3

    assert classify_sea_state(1.8)["category"] == "Moderate"
    assert classify_sea_state(1.8)["wmo_code"] == 4

    assert classify_sea_state(3.2)["category"] == "Rough"
    assert classify_sea_state(3.2)["wmo_code"] == 5

    assert classify_sea_state(5.0)["category"] == "Very rough"
    assert classify_sea_state(5.0)["wmo_code"] == 6

    assert classify_sea_state(7.5)["category"] == "High"
    assert classify_sea_state(7.5)["wmo_code"] == 7

    assert classify_sea_state(11.0)["category"] == "Very high"
    assert classify_sea_state(11.0)["wmo_code"] == 8

    assert classify_sea_state(16.0)["category"] == "Phenomenal"
    assert classify_sea_state(16.0)["wmo_code"] == 9

    assert classify_sea_state(None)["category"] == "UNKNOWN"
    assert classify_sea_state(-1.0)["category"] == "INVALID"


@pytest.mark.parametrize(
    "wave_heights_dataset",
    [
        # Live 24-hour forecast dataset from Arabian Sea API response
        [
            0.94, 0.94, 0.92, 0.92, 0.92, 0.92, 0.92, 0.92,
            0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90,
            0.92, 0.92, 0.94, 0.94, 0.96, 0.96, 0.96, 0.98,
        ],
        # 24-hour dataset whose mean is ~0.9317 m (sum 22.36)
        [
            0.94, 0.94, 0.92, 0.92, 0.92, 0.92, 0.92, 0.92,
            0.90, 0.90, 0.92, 0.92, 0.92, 0.92, 0.95, 0.95,
            0.92, 0.92, 0.94, 0.94, 0.96, 0.96, 0.96, 0.98,
        ],
    ],
)
def test_timeseries_consistency_regression(monkeypatch, wave_heights_dataset):
    """Regression test ensuring min, max, average, and latest are computed directly
    from the validated time series without hardcoded expectations.
    """
    now_utc = datetime.now(timezone.utc)

    async def fake_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id=f"ev-{idx:03d}",
                source="open-meteo-marine",
                source_record_id=f"2026-10-11T{idx:02d}:00:{latitude}:{longitude}",
                variable="wave_height",
                value=val,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 11, idx, 0, 0, tzinfo=timezone.utc),
                retrieved_at=now_utc,
                status="valid",
                quality_flags=["forecast_data"],
            )
            for idx, val in enumerate(wave_heights_dataset)
        ]

    monkeypatch.setattr(workflow.provider, "fetch", fake_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={
            "location_name": "Offshore Arabian Sea (Goa)",
            "latitude": 15.0,
            "longitude": 72.0,
            "forecast_time_window_hours": 24,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Extract time series points from response
    timeseries = data["measurements"]["timeseries"]
    assert len(timeseries) == len(wave_heights_dataset)

    # Compute expected statistics dynamically from the validated time series (no hardcoding)
    ts_values = [pt["wave_height"] for pt in timeseries if pt["wave_height"] is not None]
    expected_count = len(ts_values)
    expected_min = round(min(ts_values), 2)
    expected_max = round(max(ts_values), 2)
    expected_avg = round(sum(ts_values) / len(ts_values), 2)
    expected_latest = round(ts_values[-1], 2)

    measurements = data["measurements"]
    assert measurements["sample_count"] == expected_count
    assert measurements["min_wave_height_m"] == expected_min
    assert measurements["max_wave_height_m"] == expected_max
    assert measurements["avg_wave_height_m"] == expected_avg
    assert measurements["latest_wave_height_m"] == expected_latest

    # Verify advisory reflects the computed average and latest values
    advisory = data["analysis"]["advisory"]
    assert f"average {expected_avg:.2f} m" in advisory
    assert f"latest {expected_latest:.2f} m" in advisory
    assert f"range from {expected_min:.2f} m to {expected_max:.2f} m" in advisory


def test_exact_24h_dataset_metrics_regression(monkeypatch):
    """Regression test asserting exact expected metrics for the 24-record dataset:
    mean ~0.9317 m (0.93 m), latest at 23:00 UTC = 0.98 m, min = 0.90 m, max = 0.98 m.
    """
    now_utc = datetime.now(timezone.utc)

    # 24 records summing to 22.36 (mean = 22.36 / 24 = 0.931667 m, rounding to 0.93 m)
    exact_dataset = [
        0.94, 0.94, 0.92, 0.92, 0.92, 0.92, 0.92, 0.92,
        0.90, 0.90, 0.92, 0.92, 0.92, 0.92, 0.95, 0.95,
        0.92, 0.92, 0.94, 0.94, 0.96, 0.96, 0.96, 0.98,
    ]

    async def fake_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id=f"ev-exact-{idx:03d}",
                source="open-meteo-marine",
                source_record_id=f"2026-10-11T{idx:02d}:00:{latitude}:{longitude}",
                variable="wave_height",
                value=val,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 11, idx, 0, 0, tzinfo=timezone.utc),
                retrieved_at=now_utc,
                status="valid",
                quality_flags=["forecast_data"],
            )
            for idx, val in enumerate(exact_dataset)
        ]

    monkeypatch.setattr(workflow.provider, "fetch", fake_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={
            "location_name": "Offshore Arabian Sea (Goa)",
            "latitude": 15.0,
            "longitude": 72.0,
            "forecast_time_window_hours": 24,
        },
    )

    assert response.status_code == 200
    data = response.json()
    m = data["measurements"]

    # Assert exact expected values
    assert m["sample_count"] == 24
    assert m["min_wave_height_m"] == 0.9
    assert m["max_wave_height_m"] == 0.98
    assert m["avg_wave_height_m"] == 0.93
    assert m["latest_wave_height_m"] == 0.98

    # Assert advisory uses the exact calculated values
    advisory = data["analysis"]["advisory"]
    assert "average 0.93 m, latest 0.98 m" in advisory
    assert "range from 0.90 m to 0.98 m" in advisory


def test_orca_analyze_endpoint_rejects_negative_and_excessive_boundaries():
    """Verify endpoint rejects negative latitude/longitude and excessive window."""
    # Latitude < -90
    resp_lat_low = client.post(
        "/api/orca/analyze",
        json={"location_name": "Low Lat", "latitude": -95.0, "longitude": 72.0},
    )
    assert resp_lat_low.status_code == 422

    # Longitude < -180
    resp_lon_low = client.post(
        "/api/orca/analyze",
        json={"location_name": "Low Lon", "latitude": 15.0, "longitude": -185.0},
    )
    assert resp_lon_low.status_code == 422

    # Window > 168 (over 7 days)
    resp_win_high = client.post(
        "/api/orca/analyze",
        json={"location_name": "High Window", "latitude": 15.0, "longitude": 72.0, "forecast_time_window_hours": 200},
    )
    assert resp_win_high.status_code == 422


@pytest.mark.asyncio
async def test_marine_graph_validate_input_node_flags_out_of_bounds():
    """Verify direct input validation node captures all coordinate and window violations."""
    state: MarineState = {
        "location_name": "Boundary Test",
        "latitude": 95.0,
        "longitude": 200.0,
        "forecast_time_window_hours": 0,
        "step_progress": [],
        "issues": [],
    }
    result = await workflow.validate_input_node(state)
    assert any("invalid_latitude: 95.0" in i for i in result["issues"])
    assert any("invalid_longitude: 200.0" in i for i in result["issues"])
    assert any("invalid_time_window_hours: 0" in i for i in result["issues"])


def test_orca_analyze_endpoint_handles_provider_timeout(monkeypatch):
    """Verify endpoint gracefully handles provider timeout without false-positive clearance."""
    async def timeout_fetch(*, latitude, longitude):
        raise httpx.TimeoutException("Connection timed out to Open-Meteo")

    monkeypatch.setattr(workflow.provider, "fetch", timeout_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={"location_name": "Timeout Location", "latitude": 15.0, "longitude": 72.0},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "insufficient_evidence"
    assert data["validation_status"]["is_valid"] is False
    assert any("data_provider_error" in i for i in data["validation_status"]["issues"])
    assert data["measurements"]["sample_count"] == 0
    assert "UNKNOWN / INCOMPLETE" in data["analysis"]["advisory"]


def test_orca_analyze_endpoint_handles_provider_connection_error(monkeypatch):
    """Verify endpoint gracefully handles network resolution failures."""
    async def connect_error_fetch(*, latitude, longitude):
        raise httpx.ConnectError("Failed to resolve marine-api.open-meteo.com")

    monkeypatch.setattr(workflow.provider, "fetch", connect_error_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={"location_name": "Connect Error Location", "latitude": 15.0, "longitude": 72.0},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "insufficient_evidence"
    assert data["validation_status"]["is_valid"] is False
    assert any("data_provider_error" in i for i in data["validation_status"]["issues"])
    assert data["measurements"]["sample_count"] == 0
    assert "UNKNOWN / INCOMPLETE" in data["analysis"]["advisory"]


def test_orca_analyze_endpoint_handles_stale_retrieval_evidence(monkeypatch):
    """Verify endpoint flags stale cached retrieval (>24 hours old) with cautionary advisory."""
    now_utc = datetime.now(timezone.utc)
    stale_retrieval = now_utc - timedelta(hours=48)

    async def stale_retrieval_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id=f"ev-stale-{idx:03d}",
                source="open-meteo-marine",
                source_record_id=f"2026-10-11T{idx:02d}:00:{latitude}:{longitude}",
                variable="wave_height",
                value=1.0,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 11, idx, 0, 0, tzinfo=timezone.utc),
                retrieved_at=stale_retrieval,
                status="valid",
                quality_flags=["forecast_data"],
            )
            for idx in range(24)
        ]

    monkeypatch.setattr(workflow.provider, "fetch", stale_retrieval_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={"location_name": "Stale Retrieval Spot", "latitude": 15.0, "longitude": 72.0},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "evidence_requires_review"
    assert data["validation_status"]["is_valid"] is False
    assert any("evidence_retrieval_stale" in i for i in data["validation_status"]["issues"])
    assert "CAUTION / EVIDENCE REQUIRES REVIEW" in data["analysis"]["advisory"]
    # Ensure no false-positive safe clearance was issued
    assert "Advisory for Stale Retrieval Spot" not in data["analysis"]["advisory"]


def test_orca_analyze_endpoint_handles_stale_status_evidence(monkeypatch):
    """Verify endpoint flags records marked with status='stale' and generates caution advisory."""
    now_utc = datetime.now(timezone.utc)

    async def stale_status_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id=f"ev-status-{idx:03d}",
                source="open-meteo-marine",
                source_record_id=f"2026-10-11T{idx:02d}:00:{latitude}:{longitude}",
                variable="wave_height",
                value=1.2,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 11, idx, 0, 0, tzinfo=timezone.utc),
                retrieved_at=now_utc,
                status="stale",
                quality_flags=["forecast_data"],
            )
            for idx in range(24)
        ]

    monkeypatch.setattr(workflow.provider, "fetch", stale_status_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={"location_name": "Stale Status Spot", "latitude": 15.0, "longitude": 72.0},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "evidence_requires_review"
    assert data["validation_status"]["is_valid"] is False
    assert any("evidence_status_stale" in i for i in data["validation_status"]["issues"])
    assert "CAUTION / EVIDENCE REQUIRES REVIEW" in data["analysis"]["advisory"]


def test_orca_analyze_endpoint_handles_all_null_forecast_values(monkeypatch):
    """Verify endpoint transitions to insufficient_evidence when all forecast values are None."""
    now_utc = datetime.now(timezone.utc)

    async def all_null_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id=f"ev-null-{idx:03d}",
                source="open-meteo-marine",
                source_record_id=f"2026-10-11T{idx:02d}:00:{latitude}:{longitude}",
                variable="wave_height",
                value=None,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 11, idx, 0, 0, tzinfo=timezone.utc),
                retrieved_at=now_utc,
                status="valid",
                quality_flags=["forecast_data"],
            )
            for idx in range(24)
        ]

    monkeypatch.setattr(workflow.provider, "fetch", all_null_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={"location_name": "Null Values Spot", "latitude": 15.0, "longitude": 72.0},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "insufficient_evidence"
    assert data["validation_status"]["is_valid"] is False
    assert data["measurements"]["sample_count"] == 0
    assert data["measurements"]["min_wave_height_m"] is None
    assert data["measurements"]["max_wave_height_m"] is None
    assert data["measurements"]["avg_wave_height_m"] is None
    assert data["measurements"]["latest_wave_height_m"] is None
    assert data["analysis"]["sea_state_category"] == "UNKNOWN"
    assert "UNKNOWN / INCOMPLETE" in data["analysis"]["advisory"]


def test_orca_analyze_endpoint_handles_partial_null_forecast_values(monkeypatch):
    """Verify endpoint preserves valid timeseries while reporting review for missing hours."""
    now_utc = datetime.now(timezone.utc)

    # 24 records, but hours 10, 11, 12, 13 have value=None (20 valid values: 0.90 to 0.98)
    partial_dataset: list[float | None] = [
        0.94, 0.94, 0.92, 0.92, 0.92, 0.92, 0.92, 0.92,
        0.90, 0.90, None, None, None, None, 0.95, 0.95,
        0.92, 0.92, 0.94, 0.94, 0.96, 0.96, 0.96, 0.98,
    ]

    async def partial_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id=f"ev-part-{idx:03d}",
                source="open-meteo-marine",
                source_record_id=f"2026-10-11T{idx:02d}:00:{latitude}:{longitude}",
                variable="wave_height",
                value=val,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime(2026, 10, 11, idx, 0, 0, tzinfo=timezone.utc),
                retrieved_at=now_utc,
                status="valid",
                quality_flags=["forecast_data"],
            )
            for idx, val in enumerate(partial_dataset)
        ]

    monkeypatch.setattr(workflow.provider, "fetch", partial_fetch)

    response = client.post(
        "/api/orca/analyze",
        json={"location_name": "Partial Null Spot", "latitude": 15.0, "longitude": 72.0},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "evidence_requires_review"
    assert data["validation_status"]["is_valid"] is False
    assert any("missing_wave_height_value" in i for i in data["validation_status"]["issues"])

    m = data["measurements"]
    assert m["sample_count"] == 20
    assert len(m["timeseries"]) == 24
    assert m["min_wave_height_m"] == 0.9
    assert m["max_wave_height_m"] == 0.98
    assert m["latest_wave_height_m"] == 0.98

    # Advisory should reflect cautionary review rather than unflagged clearance
    assert "CAUTION / EVIDENCE REQUIRES REVIEW" in data["analysis"]["advisory"]