"""数据模型层 (pydantic)。

约定:
  - 这里只声明结构, 不做业务校验 (用户明确要求不校验)。
  - 卡片的展示字符串由 property 派生, 只做格式化, 不决定样式。
  - UI 层 (food_card.py / init.py) 只消费模型, 不反向写。
"""
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_CROWD_COLOR = "#8E8E93"

# data/ 固定在项目根目录, 以本文件位置为锚点, 不依赖启动时的 cwd
_PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = _PROJECT_ROOT / "data" / "foods.json"


class FoodInfo(BaseModel):
    """一条食物记录。字段与 PolishedFoodCard 的构造参数一一对应。"""

    food_id: int
    title: str
    tag_str: str = ""
    wait_mins: int = 0
    distance_km: int = 0
    base_price: int = 0
    extra_price_info: str = ""
    crowd_color: str = DEFAULT_CROWD_COLOR
    food_component: list[str] = []

    # ---- 派生展示字符串: 只格式化, 不含样式决策 ----

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
        # pydantic v2: model_dump 而不是 v1 的 dict()
        return self.model_dump()


class Coupon(BaseModel):
    """优惠券: 只声明"满多少减多少"这条规则, 计算收在 compute() 里。

    刻意保持两个字段, 不引入 code/过期时间等业务维度 —— UI 层拿到的就是一个可算的模型。
    """

    threshold: int = 0   # 满多少才可用
    discount: int = 0    # 满足后减多少

    @property
    def display(self) -> str:
        """给顾客看的文案, 同时充当 dropdown 的 values 字符串。"""
        return f"满{self.threshold}减{self.discount}"

    def compute(self, total: int) -> int:
        """返回实际减免金额。

        规则:
          - total 或 discount 非正 -> 视为脏数据, 返回 0;
          - total 低于门槛 -> 不可用, 返回 0;
          - 减免额不能把总价减成负数 -> 上限就是 total。
        """
        logging.debug(f"[Coupon.compute] entry threshold={self.threshold!r} discount={self.discount!r} total={total!r}")

        if total <= 0:
            logging.warning(f"[Coupon.compute] branch=empty-total total={total!r}, 无消费可减免")
            return 0
        if self.discount <= 0:
            logging.warning(f"[Coupon.compute] branch=no-discount discount={self.discount!r}")
            return 0
        if total < self.threshold:
            logging.debug(f"[Coupon.compute] branch=below-threshold total={total!r} < threshold={self.threshold!r}")
            return 0

        cut = min(self.discount, total)
        logging.debug(f"[Coupon.compute] branch=applied total={total!r} cut={cut!r} payable={total - cut!r}")
        return cut


class AppData(BaseModel):
    foods: list[FoodInfo] = Field(default_factory=list)
    coupons: list[Coupon] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def coupon_by_display(self, display: str) -> Coupon | None:
        """从 dropdown 的字符串反查 Coupon, 找不到返回 None 而不是抛异常。"""
        logging.debug(f"[AppData.coupon_by_display] entry display={display!r} total={len(self.coupons)}")
        for coupon in self.coupons:
            if coupon.display == display:
                logging.debug(f"[AppData.coupon_by_display] branch=hit display={display!r}")
                return coupon
        logging.warning(f"[AppData.coupon_by_display] branch=miss display={display!r}")
        return None


def load_app_data(path: Path | str = DEFAULT_DATA_PATH) -> AppData:
    data_path = Path(path)
    logging.debug(f"[load_app_data] entry path={str(data_path)!r} exists={data_path.exists()}")

    if not data_path.exists():
        return AppData(foods=[])

    try:
        raw_text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        return AppData(foods=[])

    logging.debug(f"[load_app_data] read ok, chars={len(raw_text)}")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logging.error(f"[load_app_data] branch=parse-error path={str(data_path)!r} exc={exc!r}, fallback to empty AppData")
        return AppData(foods=[])

    logging.debug(f"[load_app_data] json parsed, top_level_type={type(payload).__name__}")

    # 允许两种写法: 顶层就是 {"foods": [...]}, 或者顶层直接是 [...] 列表
    if isinstance(payload, list):
        logging.debug(f"[load_app_data] branch=bare-list, wrap into AppData.foods len={len(payload)}")
        payload = {"foods": payload}
    elif isinstance(payload, dict):
        logging.debug(f"[load_app_data] branch=object, keys={sorted(payload.keys())}")
    else:
        return AppData(foods=[])

    try:
        data = AppData.model_validate(payload)
    except Exception as exc:
        logging.error(f"[load_app_data] branch=model-invalid path={str(data_path)!r} exc={exc!r}, fallback to empty AppData")
        return AppData(foods=[])

    logging.debug(f"[load_app_data] branch=loaded foods={len(data.foods)}")
    logging.debug("[load_app_data] exit")
    return data


def save_app_data(data: AppData, path: Path | str = DEFAULT_DATA_PATH) -> bool:
    """把 AppData 写回 JSON。成功返回 True。"""
    data_path = Path(path)
    logging.debug(f"[save_app_data] entry path={str(data_path)!r} foods={len(data.foods)}")
    try:
        data_path.parent.mkdir(parents=True, exist_ok=True)
        logging.debug(f"[save_app_data] branch=mkdir-ok dir={str(data_path.parent)!r}")
        data_path.write_text(
            json.dumps(data.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logging.error(f"[save_app_data] branch=write-error path={str(data_path)!r} exc={exc!r}")
        return False

    logging.debug(f"[save_app_data] branch=saved path={str(data_path)!r}")
    return True
