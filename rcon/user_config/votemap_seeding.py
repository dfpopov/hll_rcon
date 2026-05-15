"""User config for the seeding-window votemap whitelist + thresholds.

Backs custom_tools/votemap_seeding.py — moves the previously-hardcoded
constants (warfare/offensive layer ids, player threshold, hour range)
into Redis so an admin can edit them via the rcongui Settings UI.

Defaults reflect the curated 7+7 starter pool that was the hardcoded
behaviour before this config existed (see custom_tools/votemap_seeding.py
docstring for editorial rationale).
"""
from typing import TypedDict

from pydantic import Field, field_validator

from rcon.user_config.utils import BaseUserConfig, key_check


# Default warfare layer ids — the 7 starter-friendly day maps.
DEFAULT_WARFARE_LAYER_IDS: list[str] = [
    "carentan_warfare",
    "kharkov_warfare",
    "kursk_warfare",
    "omahabeach_warfare",
    "stmariedumont_warfare",
    "stmereeglise_warfare",
    "utahbeach_warfare",
]

# Default offensive layer ids — one per base map, canonical attacker
# side (US for D-Day, RUS for Kharkov 1943, GER for Kursk Citadel).
# Note: Stmariedumont uses CRCON's abbreviated '_off_' naming, while the
# others use '_offensive_'. Both verified against rcon.maps.LAYERS.
DEFAULT_OFFENSIVE_LAYER_IDS: list[str] = [
    "carentan_offensive_us",
    "kharkov_offensive_rus",
    "kursk_offensive_ger",
    "omahabeach_offensive_us",
    "stmariedumont_off_us",
    "stmereeglise_offensive_us",
    "utahbeach_offensive_us",
]


class VotemapSeedingType(TypedDict):
    enabled: bool
    player_threshold: int
    seeding_hour_start: int
    seeding_hour_end: int
    warfare_layer_ids: list[str]
    offensive_layer_ids: list[str]


class VotemapSeedingUserConfig(BaseUserConfig):
    """Editable seeding config. Read by custom_tools/votemap_seeding.py
    on every votemap whitelist call (cheap Redis lookup)."""

    enabled: bool = Field(
        default=True,
        title="Enabled",
        description=(
            "Master switch for the seeding-window whitelist gate. "
            "When OFF the admin's full prime-time whitelist is always "
            "used (no narrowing during low pop or late hours)."
        ),
    )

    player_threshold: int = Field(
        default=50,
        ge=0,
        le=100,
        title="Player threshold",
        description=(
            "Below this many players, the seeding whitelist applies. "
            "At or above, the prime-time whitelist applies. Hard cutoff "
            "(e.g. 49 = seeding, 50 = prime)."
        ),
    )

    seeding_hour_start: int = Field(
        default=23,
        ge=0,
        le=23,
        title="Seeding hour start (Kyiv local)",
        description=(
            "Inclusive Kyiv-local hour when the time gate opens. "
            "The window spans midnight if start > end (e.g. 23..6 means "
            "23:00–05:59). Pure player-count gating: set start = end."
        ),
    )

    seeding_hour_end: int = Field(
        default=6,
        ge=0,
        le=23,
        title="Seeding hour end (Kyiv local)",
        description=(
            "Exclusive Kyiv-local hour when the time gate closes."
        ),
    )

    warfare_layer_ids: list[str] = Field(
        default_factory=lambda: list(DEFAULT_WARFARE_LAYER_IDS),
        title="Seeding warfare layer ids",
        description=(
            "Layer ids (NOT base map ids) that may appear as warfare "
            "options during the seeding window. Combined with admin's "
            "num_warfare_options, votemap picks N warfares from this list."
        ),
    )

    offensive_layer_ids: list[str] = Field(
        default_factory=lambda: list(DEFAULT_OFFENSIVE_LAYER_IDS),
        title="Seeding offensive layer ids",
        description=(
            "Layer ids that may appear as offensive options during the "
            "seeding window. Combined with admin's num_offensive_options, "
            "votemap picks N offensives from this list. The dedup wrapper "
            "ensures the chosen offensive's base map does not duplicate "
            "any warfare slot in the same vote."
        ),
    )

    @field_validator("warfare_layer_ids", "offensive_layer_ids")
    @classmethod
    def _strip_and_dedupe(cls, vs: list[str]) -> list[str]:
        # Trim whitespace and drop empties, preserve order, dedupe.
        seen: set[str] = set()
        out: list[str] = []
        for v in vs or []:
            v = (v or "").strip()
            if not v or v in seen:
                continue
            seen.add(v)
            out.append(v)
        return out

    @staticmethod
    def save_to_db(values: VotemapSeedingType, dry_run: bool = False) -> None:
        key_check(
            VotemapSeedingType.__required_keys__,
            VotemapSeedingType.__optional_keys__,
            values.keys(),
        )
        validated = VotemapSeedingUserConfig(
            enabled=values.get("enabled"),
            player_threshold=values.get("player_threshold"),
            seeding_hour_start=values.get("seeding_hour_start"),
            seeding_hour_end=values.get("seeding_hour_end"),
            warfare_layer_ids=values.get("warfare_layer_ids"),
            offensive_layer_ids=values.get("offensive_layer_ids"),
        )
        if not dry_run:
            from rcon.user_config.utils import set_user_config
            set_user_config(validated.KEY(), validated.model_dump())
