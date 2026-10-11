"""Documented Marine Fisheries Species Registry & Environmental Bounds.

Scientific Standards & Citations:
1. Central Marine Fisheries Research Institute (CMFRI), ICAR, India:
   - Marine Fisheries Information Service Technical & Extension Series.
   - Species profiles for Indian Mackerel (Rastrelliger kanagurta) and Indian Oil Sardine (Sardinella longiceps).
2. Indian National Centre for Ocean Information Services (INCOIS):
   - Potential Fishing Zone (PFZ) Advisory Validation Manual:
     Uses Sea Surface Temperature (SST from NOAA-AVHRR / MODIS) and Chlorophyll-a (OceanSat / VIIRS) composite fronts.
3. Food and Agriculture Organization (FAO) Fisheries Species Catalogs:
   - Vol. 2: Scombroids of the World (Collette & Nauen, 1983) for Thunnus albacares (Yellowfin Tuna).
4. Indian Ocean Tuna Commission (IOTC):
   - Scientific Committee Reports on tropical tuna habitat and thermal preferences.
"""

from typing import Any

SPECIES_REGISTRY: dict[str, dict[str, Any]] = {
    "mackerel": {
        "key": "mackerel",
        "common_name": "Indian Mackerel",
        "scientific_name": "Rastrelliger kanagurta",
        "family": "Scombridae",
        "aliases": ["mackerel", "indian mackerel", "rastrelliger", "rastrelliger kanagurta", "bangda"],
        "sst_optimal_min_c": 26.0,
        "sst_optimal_max_c": 30.0,
        "sst_tolerable_min_c": 24.0,
        "sst_tolerable_max_c": 31.5,
        "depth_range_m": "10-50 m (coastal neritic, epipelagic)",
        "citation": "CMFRI Species Profile / INCOIS PFZ Operational Guidelines",
        "habitat_notes": (
            "Coastal neritic waters, schooling epipelagic, planktivorous feeding on copepods and diatom blooms. "
            "Strongly associated with thermal gradient fronts and post-monsoon upwelling."
        ),
    },
    "tuna": {
        "key": "tuna",
        "common_name": "Yellowfin Tuna / Oceanic Tuna",
        "scientific_name": "Thunnus albacares",
        "family": "Scombridae",
        "aliases": ["tuna", "yellowfin", "yellowfin tuna", "thunnus", "thunnus albacares", "skipjack", "kera"],
        "sst_optimal_min_c": 24.0,
        "sst_optimal_max_c": 29.0,
        "sst_tolerable_min_c": 21.0,
        "sst_tolerable_max_c": 31.0,
        "depth_range_m": "0-250 m (epipelagic / upper mesopelagic continental shelf break)",
        "citation": "FAO Fisheries Synopsis No. 125, Vol. 2; IOTC Scientific Reports",
        "habitat_notes": (
            "Highly migratory oceanic pelagic. Aggregates around shelf breaks, seamounts, "
            "and thermal convergence fronts with deep mixed layers."
        ),
    },
    "sardine": {
        "key": "sardine",
        "common_name": "Indian Oil Sardine",
        "scientific_name": "Sardinella longiceps",
        "family": "Clupeidae",
        "aliases": ["sardine", "oil sardine", "indian oil sardine", "sardinella", "sardinella longiceps", "tarli"],
        "sst_optimal_min_c": 27.0,
        "sst_optimal_max_c": 30.0,
        "sst_tolerable_min_c": 25.0,
        "sst_tolerable_max_c": 31.5,
        "depth_range_m": "5-35 m (shallow coastal pelagic)",
        "citation": "CMFRI Bulletin No. 16; Pillai et al., Indian J. Fish.",
        "habitat_notes": (
            "Schooling clupeid in coastal waters. Feeds primarily on phytoplankton (Fragilariopsis, Coscinodiscus). "
            "Abundance strongly linked to coastal monsoonal upwelling and diatom blooms."
        ),
    },
    "bombay duck": {
        "key": "bombay duck",
        "common_name": "Bombay Duck",
        "scientific_name": "Harpadon nehereus",
        "family": "Synodontidae",
        "aliases": ["bombay duck", "bombil", "harpadon", "harpadon nehereus"],
        "sst_optimal_min_c": 25.0,
        "sst_optimal_max_c": 29.0,
        "sst_tolerable_min_c": 23.0,
        "sst_tolerable_max_c": 31.0,
        "depth_range_m": "10-50 m (demersal, shelf/estuarine)",
        "citation": "CMFRI Marine Fisheries Information Service No. 102",
        "habitat_notes": (
            "Demersal carnivore inhabiting soft muddy bottom substrates in continental shelf and estuarine zones. "
            "Sensitive to extreme salinity swings and bottom thermal variations."
        ),
    },
}


def lookup_species(target_species: str | None) -> dict[str, Any]:
    """Look up target species in documented marine registry.

    Returns structured status, matching info, or unsupported flag.
    """
    if not target_species or not target_species.strip():
        return {
            "status": "GENERAL",
            "queried_name": None,
            "resolved_name": "General Pelagic/Demersal",
            "species_info": None,
            "note": "No target species specified; assessing general marine fisheries environmental indicators.",
        }

    query = target_species.strip().lower()

    # Exact key or alias match
    for species_key, info in SPECIES_REGISTRY.items():
        if query == species_key:
            return {
                "status": "SUPPORTED",
                "queried_name": target_species,
                "resolved_name": info["common_name"],
                "species_info": info,
                "note": f"Species '{info['common_name']}' ({info['scientific_name']}) recognized in documented registry.",
            }
        for alias in info["aliases"]:
            if alias in query or query in alias:
                return {
                    "status": "SUPPORTED",
                    "queried_name": target_species,
                    "resolved_name": info["common_name"],
                    "species_info": info,
                    "note": f"Species '{info['common_name']}' ({info['scientific_name']}) recognized via alias match.",
                }

    supported_names = [f"{s['common_name']} ({s['scientific_name']})" for s in SPECIES_REGISTRY.values()]
    return {
        "status": "UNSUPPORTED",
        "queried_name": target_species,
        "resolved_name": target_species,
        "species_info": None,
        "supported_species": supported_names,
        "note": (
            f"Target species '{target_species}' is not documented in the tropical marine registry. "
            f"Documented species include: {', '.join(supported_names)}."
        ),
    }


def evaluate_thermal_suitability(
    species_lookup: dict[str, Any],
    sst_c: float | None,
) -> dict[str, Any]:
    """Evaluate sea-surface temperature against documented species bounds.

    Returns thermal suitability category, sub-score (0-100), and rationale.
    Does NOT claim fish are present; evaluates environmental habitat boundary only.
    """
    if sst_c is None:
        return {
            "thermal_suitability": "UNKNOWN",
            "thermal_sub_score": None,
            "observed_sst_c": None,
            "status": "MISSING_EVIDENCE",
            "rationale": "Sea-surface temperature telemetry is unavailable.",
        }

    # Physical plausibility check
    if sst_c < -2.0 or sst_c > 45.0:
        return {
            "thermal_suitability": "INVALID",
            "thermal_sub_score": None,
            "observed_sst_c": sst_c,
            "status": "PHYSICALLY_INVALID",
            "rationale": f"Observed SST ({sst_c:.1f}°C) is physically implausible for marine waters.",
        }

    status = species_lookup.get("status")
    species_info = species_lookup.get("species_info")

    if status == "SUPPORTED" and species_info:
        opt_min = species_info["sst_optimal_min_c"]
        opt_max = species_info["sst_optimal_max_c"]
        tol_min = species_info["sst_tolerable_min_c"]
        tol_max = species_info["sst_tolerable_max_c"]
        common_name = species_info["common_name"]

        if opt_min <= sst_c <= opt_max:
            return {
                "thermal_suitability": "OPTIMAL",
                "thermal_sub_score": 95.0,
                "observed_sst_c": round(sst_c, 2),
                "optimal_range_c": [opt_min, opt_max],
                "tolerable_range_c": [tol_min, tol_max],
                "status": "VALID",
                "rationale": (
                    f"Observed SST ({sst_c:.1f}°C) is within optimal thermal range "
                    f"({opt_min:.1f}°C - {opt_max:.1f}°C) for {common_name}."
                ),
                "citation": species_info["citation"],
            }
        elif tol_min <= sst_c <= tol_max:
            # Linear scaling between 50 and 85
            if sst_c < opt_min:
                fraction = (sst_c - tol_min) / (opt_min - tol_min)
            else:
                fraction = (tol_max - sst_c) / (tol_max - opt_max)
            sub_score = round(50.0 + (35.0 * fraction), 1)

            return {
                "thermal_suitability": "TOLERABLE",
                "thermal_sub_score": sub_score,
                "observed_sst_c": round(sst_c, 2),
                "optimal_range_c": [opt_min, opt_max],
                "tolerable_range_c": [tol_min, tol_max],
                "status": "VALID",
                "rationale": (
                    f"Observed SST ({sst_c:.1f}°C) is within tolerable thermal range "
                    f"({tol_min:.1f}°C - {tol_max:.1f}°C) for {common_name}, outside optimal."
                ),
                "citation": species_info["citation"],
            }
        else:
            return {
                "thermal_suitability": "UNFAVORABLE",
                "thermal_sub_score": 20.0,
                "observed_sst_c": round(sst_c, 2),
                "optimal_range_c": [opt_min, opt_max],
                "tolerable_range_c": [tol_min, tol_max],
                "status": "VALID",
                "rationale": (
                    f"Observed SST ({sst_c:.1f}°C) is outside tolerable thermal range "
                    f"({tol_min:.1f}°C - {tol_max:.1f}°C) for {common_name}."
                ),
                "citation": species_info["citation"],
            }

    elif status == "UNSUPPORTED":
        return {
            "thermal_suitability": "UNKNOWN",
            "thermal_sub_score": None,
            "observed_sst_c": round(sst_c, 2),
            "status": "UNSUPPORTED_SPECIES",
            "rationale": (
                f"Observed SST is {sst_c:.1f}°C, but species '{species_lookup['queried_name']}' "
                "lacks documented thermal preference ranges in the registry."
            ),
        }
    else:  # GENERAL
        # General tropical epipelagic standard (25.0 - 29.5 °C)
        if 25.0 <= sst_c <= 29.5:
            return {
                "thermal_suitability": "FAVORABLE (GENERAL)",
                "thermal_sub_score": 85.0,
                "observed_sst_c": round(sst_c, 2),
                "optimal_range_c": [25.0, 29.5],
                "status": "VALID",
                "rationale": (
                    f"Observed SST ({sst_c:.1f}°C) is within standard tropical shelf waters range (25.0 - 29.5°C)."
                ),
            }
        elif 22.0 <= sst_c <= 31.5:
            return {
                "thermal_suitability": "MODERATE (GENERAL)",
                "thermal_sub_score": 60.0,
                "observed_sst_c": round(sst_c, 2),
                "optimal_range_c": [25.0, 29.5],
                "status": "VALID",
                "rationale": f"Observed SST ({sst_c:.1f}°C) is within broader tropical marine thermal bounds.",
            }
        else:
            return {
                "thermal_suitability": "UNFAVORABLE (GENERAL)",
                "thermal_sub_score": 25.0,
                "observed_sst_c": round(sst_c, 2),
                "status": "VALID",
                "rationale": f"Observed SST ({sst_c:.1f}°C) is outside typical tropical marine fishery bounds.",
            }
