"""Documented Marine Meteorological Sea State Rules.

Standards & Citations:
1. World Meteorological Organization (WMO) Code Table 3700: State of the sea.
   Reference: WMO-No. 306, Manual on Codes, Volume I.1, Part A.
2. Douglas Sea Scale (UK Hydrographic Office / British Admiralty).

These rules map significant wave height (Hs) in meters directly to international
meteorological sea-state categories without arbitrary or unreviewed thresholds.
"""

from typing import Any, TypedDict


class SeaStateRule(TypedDict):
    code: int
    category: str
    min_m: float
    max_m: float
    description: str


WMO_SEA_STATE_TABLE: list[SeaStateRule] = [
    {
        "code": 0,
        "category": "Calm (glassy)",
        "min_m": 0.0,
        "max_m": 0.0,
        "description": "Sea surface like a mirror.",
    },
    {
        "code": 1,
        "category": "Calm (rippled)",
        "min_m": 0.0,
        "max_m": 0.1,
        "description": "Ripples with appearance of scales; no foam crests.",
    },
    {
        "code": 2,
        "category": "Smooth",
        "min_m": 0.1,
        "max_m": 0.5,
        "description": "Small wavelets; short and pronounced, glassy crests.",
    },
    {
        "code": 3,
        "category": "Slight",
        "min_m": 0.5,
        "max_m": 1.25,
        "description": "Large wavelets; crests begin to break, scattered white foam.",
    },
    {
        "code": 4,
        "category": "Moderate",
        "min_m": 1.25,
        "max_m": 2.5,
        "description": "Small waves, becoming longer; fairly frequent white crests.",
    },
    {
        "code": 5,
        "category": "Rough",
        "min_m": 2.5,
        "max_m": 4.0,
        "description": "Moderate waves taking pronounced longer form; frequent white spray.",
    },
    {
        "code": 6,
        "category": "Very rough",
        "min_m": 4.0,
        "max_m": 6.0,
        "description": "Large waves heap up; extensive white foam crests blown in wind.",
    },
    {
        "code": 7,
        "category": "High",
        "min_m": 6.0,
        "max_m": 9.0,
        "description": "Sea heaps up; white foam streaks blown along the direction of the wind.",
    },
    {
        "code": 8,
        "category": "Very high",
        "min_m": 9.0,
        "max_m": 14.0,
        "description": "Moderately high waves of great length; crests break into spindrift.",
    },
    {
        "code": 9,
        "category": "Phenomenal",
        "min_m": 14.0,
        "max_m": float("inf"),
        "description": "Exceptionally high waves; sea completely covered with white foam patches.",
    },
]


def classify_sea_state(wave_height_m: float | None) -> dict[str, Any]:
    """Classify significant wave height (Hs) using WMO Code Table 3700.

    Returns structured classification or UNKNOWN if wave height is null or negative.
    """
    if wave_height_m is None:
        return {
            "wmo_code": None,
            "category": "UNKNOWN",
            "description": "No wave height measurement available.",
            "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
        }

    if wave_height_m < 0:
        return {
            "wmo_code": None,
            "category": "INVALID",
            "description": "Negative wave height measurement is physically invalid.",
            "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
        }

    if wave_height_m == 0.0:
        return {
            "wmo_code": 0,
            "category": "Calm (glassy)",
            "description": "Sea surface like a mirror.",
            "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
        }

    for entry in WMO_SEA_STATE_TABLE[1:]:
        min_m: float = entry["min_m"]
        max_m: float = entry["max_m"]
        if min_m < wave_height_m <= max_m:
            return {
                "wmo_code": entry["code"],
                "category": entry["category"],
                "description": entry["description"],
                "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
            }

    return {
        "wmo_code": 9,
        "category": "Phenomenal",
        "description": "Exceptionally high waves; sea completely covered with white foam patches.",
        "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
    }
