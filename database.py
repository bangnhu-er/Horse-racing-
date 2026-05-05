import json
import os
from threading import Lock


class Database:
    """
    Database JSON lưu:
      - balances    : {user_id: int}
      - inventories : {user_id: {item_id: int}}   ← TÚI ĐỒ
      - lb_items    : {user_id: int}               ← Số đạo cụ BXH tích lũy
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._lock = Lock()
        self._data: dict = {}
        self._load()

    # ─── I/O ───────────────────────────────────────────────────────────────
    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}
        if "balances" not in self._data:
            self._data["balances"] = {}
        if "inventories" not in self._data:
            self._data["inventories"] = {}
        if "lb_items" not in self._data:
            self._data["lb_items"] = {}

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"❌ Lỗi lưu database: {e}")

    # ─── BALANCE ───────────────────────────────────────────────────────────
    def get_balance(self, user_id: str, default: int = 1000) -> int:
        with self._lock:
            bal = self._data["balances"]
            if user_id not in bal:
                bal[user_id] = default
                self._save()
            return bal[user_id]

    def set_balance(self, user_id: str, amount: int):
        with self._lock:
            self._data["balances"][user_id] = max(0, amount)
            self._save()

    def add_balance(self, user_id: str, amount: int, default: int = 1000):
        current = self.get_balance(user_id, default)
        self.set_balance(user_id, current + amount)

    def subtract_balance(self, user_id: str, amount: int, default: int = 1000) -> bool:
        current = self.get_balance(user_id, default)
        if current < amount:
            return False
        self.set_balance(user_id, current - amount)
        return True

    def get_all(self) -> dict:
        """Trả về dict {user_id: balance} để dùng cho leaderboard coin."""
        with self._lock:
            return dict(self._data["balances"])

    def reset_balance(self, user_id: str, default: int = 1000):
        self.set_balance(user_id, default)

    # ─── INVENTORY (TÚI ĐỒ) ───────────────────────────────────────────────
    def get_inventory(self, user_id: str) -> dict:
        """Trả về {item_id: quantity}"""
        with self._lock:
            return dict(self._data["inventories"].get(user_id, {}))

    def add_item(self, user_id: str, item_id: str, qty: int = 1):
        """Thêm đạo cụ vào túi."""
        with self._lock:
            inv = self._data["inventories"]
            if user_id not in inv:
                inv[user_id] = {}
            inv[user_id][item_id] = inv[user_id].get(item_id, 0) + qty
            self._save()

    def remove_item(self, user_id: str, item_id: str, qty: int = 1) -> bool:
        """
        Xóa bớt đạo cụ. Trả về False nếu không đủ.
        Tự xóa key khi về 0.
        """
        with self._lock:
            inv = self._data["inventories"]
            current = inv.get(user_id, {}).get(item_id, 0)
            if current < qty:
                return False
            inv[user_id][item_id] = current - qty
            if inv[user_id][item_id] == 0:
                del inv[user_id][item_id]
            self._save()
            return True

    def has_item(self, user_id: str, item_id: str) -> bool:
        return self.get_inventory(user_id).get(item_id, 0) > 0

    # ─── LB_ITEMS (đạo cụ phần thưởng BXH, chờ nhận) ─────────────────────
    def get_lb_items(self, user_id: str) -> int:
        with self._lock:
            return self._data["lb_items"].get(user_id, 0)

    def add_lb_items(self, user_id: str, qty: int):
        with self._lock:
            self._data["lb_items"][user_id] = self._data["lb_items"].get(user_id, 0) + qty
            self._save()

    def clear_lb_items(self, user_id: str):
        with self._lock:
            self._data["lb_items"][user_id] = 0
            self._save()
