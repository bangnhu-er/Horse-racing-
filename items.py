"""
items.py — Hệ thống đạo cụ cho bot đua ngựa

Phân loại:
  BOOST  → tăng tỉ lệ thắng của ngựa được chọn (giảm nhân tiền một chút)
  DEBUFF → giảm tỉ lệ thắng của ngựa được chọn (tăng nhân tiền lên)

Mỗi item có:
  - id          : mã định danh duy nhất (string)
  - name        : tên hiển thị
  - emoji       : biểu tượng
  - description : mô tả ngắn
  - item_type   : "boost" hoặc "debuff"
  - win_delta   : thay đổi tỉ lệ thắng (float, dương = tăng, âm = giảm)
  - mult_delta  : thay đổi hệ số nhân (float, dương = tăng, âm = giảm)
  - rarity      : "common" | "rare" | "epic"
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    emoji: str
    description: str
    item_type: str      # "boost" | "debuff"
    win_delta: float    # thay đổi tỉ lệ thắng (ví dụ +0.08 = +8%)
    mult_delta: float   # thay đổi hệ số nhân (ví dụ -0.3 = -×0.3)
    rarity: str         # "common" | "rare" | "epic"


# ========== DANH SÁCH TẤT CẢ ĐẠO CỤ ==========
ALL_ITEMS: list[Item] = [

    # ── BOOST — tăng tỉ lệ thắng, giảm nhân ──
    Item(
        id="carrot",
        name="Củ Cà Rốt",
        emoji="🥕",
        description="Cho ngựa ăn cà rốt, tăng nhẹ tốc độ.",
        item_type="boost",
        win_delta=+0.05,
        mult_delta=-0.2,
        rarity="common",
    ),
    Item(
        id="horseshoe",
        name="Móng Ngựa Vàng",
        emoji="🧲",
        description="Móng ngựa may mắn, tăng đáng kể tỉ lệ về nhất.",
        item_type="boost",
        win_delta=+0.10,
        mult_delta=-0.5,
        rarity="rare",
    ),
    Item(
        id="energy_drink",
        name="Nước Tăng Lực",
        emoji="⚡",
        description="Uống một hơi, ngựa chạy như điện!",
        item_type="boost",
        win_delta=+0.15,
        mult_delta=-0.8,
        rarity="epic",
    ),
    Item(
        id="lucky_clover",
        name="Lá Bốn Lá",
        emoji="🍀",
        description="Lá clover may mắn hiếm gặp, tăng nhẹ cơ hội thắng.",
        item_type="boost",
        win_delta=+0.07,
        mult_delta=-0.3,
        rarity="common",
    ),
    Item(
        id="wind_cape",
        name="Áo Choàng Gió",
        emoji="🌬️",
        description="Choàng lên ngựa, giảm ma sát không khí đáng kể.",
        item_type="boost",
        win_delta=+0.12,
        mult_delta=-0.6,
        rarity="rare",
    ),

    # ── DEBUFF — giảm tỉ lệ thắng, tăng nhân (cược rủi ro cao) ──
    Item(
        id="heavy_saddle",
        name="Yên Ngựa Nặng",
        emoji="🪨",
        description="Đặt yên nặng lên ngựa đối thủ, giảm tốc đáng kể.",
        item_type="debuff",
        win_delta=-0.08,
        mult_delta=+0.5,
        rarity="common",
    ),
    Item(
        id="sleep_hay",
        name="Cỏ Gây Ngủ",
        emoji="😴",
        description="Cho ngựa ăn cỏ buồn ngủ trước khi đua.",
        item_type="debuff",
        win_delta=-0.12,
        mult_delta=+0.8,
        rarity="rare",
    ),
    Item(
        id="broken_shoe",
        name="Móng Bị Gãy",
        emoji="💔",
        description="Móng ngựa bị hỏng, tốc độ giảm mạnh — nhưng nhân cực cao!",
        item_type="debuff",
        win_delta=-0.18,
        mult_delta=+1.5,
        rarity="epic",
    ),
    Item(
        id="mud_boots",
        name="Ủng Bùn",
        emoji="🥾",
        description="Chân ngựa bị dính bùn, chạy chậm hơn.",
        item_type="debuff",
        win_delta=-0.06,
        mult_delta=+0.4,
        rarity="common",
    ),
    Item(
        id="blindfold",
        name="Khăn Bịt Mắt",
        emoji="🙈",
        description="Bịt mắt ngựa, không thấy đường về đích!",
        item_type="debuff",
        win_delta=-0.15,
        mult_delta=+1.2,
        rarity="rare",
    ),
]

# Map id → Item để tra nhanh
ITEM_MAP: dict[str, Item] = {item.id: item for item in ALL_ITEMS}

# Trọng số rarity khi drop từ daily
RARITY_WEIGHTS = {
    "common": 65,
    "rare":   28,
    "epic":    7,
}

RARITY_EMOJI = {
    "common": "⚪",
    "rare":   "🔵",
    "epic":   "🟣",
}

RARITY_LABEL = {
    "common": "Thường",
    "rare":   "Hiếm",
    "epic":   "Sử Thi",
}

TYPE_EMOJI = {
    "boost":  "📈",
    "debuff": "📉",
}


def get_random_item() -> Item:
    """Chọn ngẫu nhiên 1 đạo cụ theo trọng số rarity."""
    import random
    rarities = list(RARITY_WEIGHTS.keys())
    weights = [RARITY_WEIGHTS[r] for r in rarities]

    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    pool = [item for item in ALL_ITEMS if item.rarity == chosen_rarity]
    return random.choice(pool)


def format_item_card(item: Item, qty: int = 1) -> str:
    """Trả về chuỗi hiển thị gọn cho 1 item."""
    r_emoji = RARITY_EMOJI[item.rarity]
    r_label = RARITY_LABEL[item.rarity]
    t_emoji = TYPE_EMOJI[item.item_type]

    delta_win = f"+{item.win_delta*100:.0f}%" if item.win_delta > 0 else f"{item.win_delta*100:.0f}%"
    delta_mul = f"+×{item.mult_delta:.1f}" if item.mult_delta > 0 else f"×{item.mult_delta:.1f}"

    qty_str = f" ×{qty}" if qty > 1 else ""
    return (
        f"{item.emoji} **{item.name}**{qty_str} {r_emoji}*{r_label}*\n"
        f"  {t_emoji} Tỉ lệ: `{delta_win}` | Nhân: `{delta_mul}`\n"
        f"  _{item.description}_"
    )
