import random
from dataclasses import dataclass, field

HORSE_NAMES = [
    ("Thần Tốc", "🐎"), ("Bão Lửa", "🔥"), ("Sấm Sét", "⚡"),
    ("Băng Tuyết", "❄️"), ("Kim Cương", "💎"), ("Hắc Long", "🐉"),
    ("Mãnh Hổ", "🐯"), ("Bạch Mã", "🦄"), ("Thiên Lôi", "🌩️"),
    ("Phượng Hoàng", "🦅"), ("Cuồng Phong", "🌪️"), ("Ngọc Bích", "🌊"),
]

# (tên, win_rate_min, win_rate_max, mult_min, mult_max)
HORSE_TIERS = [
    ("Siêu Mạnh", 0.40, 0.55, 1.5, 2.0),
    ("Mạnh",      0.25, 0.40, 2.0, 3.5),
    ("Trung Bình",0.15, 0.25, 3.5, 5.5),
    ("Yếu",       0.08, 0.15, 5.5, 8.0),
    ("Cực Yếu",   0.03, 0.10, 8.0, 10.0),
]

# Giới hạn an toàn sau khi áp đạo cụ
WIN_RATE_MIN = 0.02
WIN_RATE_MAX = 0.75
MULT_MIN     = 1.2
MULT_MAX     = 12.0


@dataclass
class Horse:
    name: str
    emoji: str
    win_rate: float
    multiplier: float
    tier: str
    # Giá trị gốc — không bị thay đổi khi áp item
    _base_win_rate: float = field(init=False, repr=False)
    _base_multiplier: float = field(init=False, repr=False)

    def __post_init__(self):
        self._base_win_rate = self.win_rate
        self._base_multiplier = self.multiplier


@dataclass
class HorseRace:
    horses: list = field(default_factory=list)
    bets: dict = field(default_factory=dict)
    # {horse_idx: [{"item_id": str, "user_id": str}, ...]}  ← danh sách, cộng dồn
    applied_items: dict = field(default_factory=dict)
    is_running: bool = False

    def __post_init__(self):
        self.horses = self._generate_horses()

    def _generate_horses(self) -> list:
        horses = []
        chosen_names = random.sample(HORSE_NAMES, 5)
        tiers = list(HORSE_TIERS)
        random.shuffle(tiers)

        for i in range(5):
            name, emoji = chosen_names[i]
            tier_name, wr_min, wr_max, mult_min, mult_max = tiers[i]

            win_rate = round(random.uniform(wr_min, wr_max), 2)
            ratio = (win_rate - wr_min) / (wr_max - wr_min) if wr_max != wr_min else 0.5
            multiplier = round(mult_max - ratio * (mult_max - mult_min), 1)
            multiplier = max(mult_min, min(mult_max, multiplier))

            horses.append(Horse(name=name, emoji=emoji, win_rate=win_rate,
                                multiplier=multiplier, tier=tier_name))

        horses.sort(key=lambda h: h.win_rate, reverse=True)
        return horses

    def add_bet(self, user_id: str, horse_num: int, amount: int):
        self.bets[user_id] = {"horse": horse_num, "amount": amount}

    def apply_item(self, horse_idx: int, item, user_id: str):
        """
        Cộng dồn hiệu ứng đạo cụ lên ngựa.
        Nhiều người có thể dùng nhiều đạo cụ lên cùng 1 ngựa — tất cả được cộng vào.
        Kết quả bị giới hạn trong [WIN_RATE_MIN, WIN_RATE_MAX] và [MULT_MIN, MULT_MAX].
        """
        horse = self.horses[horse_idx]

        new_wr = round(horse.win_rate + item.win_delta, 2)
        new_wr = max(WIN_RATE_MIN, min(WIN_RATE_MAX, new_wr))

        new_mult = round(horse.multiplier + item.mult_delta, 1)
        new_mult = max(MULT_MIN, min(MULT_MAX, new_mult))

        horse.win_rate = new_wr
        horse.multiplier = new_mult

        # Ghi vào danh sách — cho phép nhiều item/ngựa
        if horse_idx not in self.applied_items:
            self.applied_items[horse_idx] = []
        self.applied_items[horse_idx].append({
            "item_id": item.id,
            "user_id": user_id,
        })

    def get_applied_count(self, horse_idx: int) -> int:
        """Số đạo cụ đã áp dụng lên ngựa này."""
        return len(self.applied_items.get(horse_idx, []))

    def determine_winner(self) -> int:
        """Chọn ngựa thắng theo trọng số win_rate (đã tính đạo cụ)."""
        total = sum(h.win_rate for h in self.horses)
        weights = [h.win_rate / total for h in self.horses]
        return random.choices(range(5), weights=weights, k=1)[0]
