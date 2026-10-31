"""Data model layer (pydantic).

Structure only, no business validation. Display strings are derived properties;
ui/ consumes these models and never writes back.
"""
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_CROWD_COLOR = "#8E8E93"

# anchored on this file, not on the cwd we happen to start from
_PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = _PROJECT_ROOT / "data" / "foods.json"


class FoodInfo(BaseModel):
    """One food record. Fields map 1:1 onto PolishedFoodCard's ctor args."""

    food_id: int
    title: str
    tag_str: str = ""
    wait_mins: int = 0
    distance_km: int = 0
    base_price: int = 0
    extra_price_info: str = ""
    crowd_color: str = DEFAULT_CROWD_COLOR
    food_component: list[str] = []

    @property
    def price_text(self) -> str:
        return f"{self.base_price}¥"

    @property
    def wait_text(self) -> str:
        return f"{self.wait_mins}min"

    @property
    def distance_text(self) -> str:
        return f"{self.distance_km}km"

    @property
    def extra_text(self) -> str:
        return self.extra_price_info

    def to_dict(self) -> dict[str, Any]:
        # pydantic v2
        return self.model_dump()


class Coupon(BaseModel):
    """Spend X, get Y off. compute() is the only arithmetic in the app."""

    threshold: int = 0
    discount: int = 0

    @property
    def display(self) -> str:
        """Dropdown string and human label, same text."""
        return f"spend {self.threshold} save {self.discount}"

    def compute(self, total: int) -> int:
        """Actual amount off; 0 when the coupon does not apply."""
        if total <= 0:
            logging.warning(f"coupon on empty total {total}")
            return 0
        if self.discount <= 0:
            return 0
        if total < self.threshold:
            logging.debug(f"below threshold: {total} < {self.threshold}")
            return 0

        cut = min(self.discount, total)
        logging.debug(f"coupon applied: total={total} cut={cut} payable={total - cut}")
        return cut


class AppData(BaseModel):
    foods: list[FoodInfo] = Field(default_factory=list)
    coupons: list[Coupon] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def coupon_by_display(self, display: str) -> Coupon | None:
        """Reverse lookup from the dropdown string; None instead of raising."""
        for coupon in self.coupons:
            if coupon.display == display:
                return coupon
        logging.warning(f"no coupon matches {display!r}")
        return None


# 'any' turns the distance criterion off; otherwise the value is a radius in km
DISTANCE_FIELD = 'distance_km'
DISTANCE_ANY = 'any'


def filter_foods(foods: list[FoodInfo], criteria: dict[str, list[str]]) -> list[FoodInfo]:
    """Return the foods that survive every active criterion.

    The three field kinds are genuinely different, so each gets its own rule:
      - list fields (food_component / allergies): a selected value EXCLUDES the food
      - distance_km: a radius, keeps foods at or under the strictest selected value
      - anything else: exact string match
    An empty selection, or 'any' for distance, means that criterion is inactive.
    """
    remaining = list(foods)
    for name, selected in criteria.items():
        wanted = set(selected)
        if not wanted:
            logging.debug(f"filter {name}: inactive, nothing selected")
            continue
        if name == DISTANCE_FIELD and DISTANCE_ANY in wanted:
            logging.debug(f"filter {name}: 'any' selected, inactive")
            continue

        max_km = None
        if name == DISTANCE_FIELD:
            max_km = min(int(v) for v in wanted)

        kept = []
        for food in remaining:
            if not hasattr(food, name):
                # filter_name must match a FoodInfo field
                logging.error(f"filter {name}: no such field on food {food.food_id}")
                continue
            field_value = getattr(food, name)
            if isinstance(field_value, (list, tuple, set)):
                # allergies: drop the food if it contains ANY selected allergen
                matched = not wanted.intersection({str(v) for v in field_value})
            elif max_km is not None:
                matched = int(field_value) <= max_km
            else:
                # menu values are strings, the model field may not be
                matched = str(field_value) in wanted
            if matched:
                kept.append(food)
        logging.debug(f"filter {name}: wanted={sorted(wanted)} kept {len(kept)}/{len(remaining)}")
        remaining = kept
    return remaining


def load_app_data(path: Path | str = DEFAULT_DATA_PATH) -> AppData:
    data_path = Path(path)
    if not data_path.exists():
        logging.error(f"data file missing: {data_path}")
        return AppData(foods=[])

    try:
        raw_text = data_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error(f"cannot read data file {data_path}: {exc}")
        return AppData(foods=[])

    # both shapes are tolerated: {"foods": [...]} or a bare list
    if isinstance(payload, list):
        payload = {"foods": payload}

    try:
        data = AppData.model_validate(payload)
    except Exception as exc:
        logging.error(f"data does not match model: {exc}")
        return AppData(foods=[])

    logging.debug(f"data loaded: foods={len(data.foods)} coupons={len(data.coupons)}")
    return data


def save_app_data(data: AppData, path: Path | str = DEFAULT_DATA_PATH) -> bool:
    """Write AppData back to JSON. True on success."""
    data_path = Path(path)
    try:
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(
            json.dumps(data.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logging.error(f"cannot write data file {data_path}: {exc}")
        return False

    logging.debug(f"data saved: {data_path}")
    return True
