import discord
from discord.ext import commands
import asyncio
import random
from typing import Optional

from horse_race import HorseRace, Horse
from database import Database
from items import (
    ALL_ITEMS, ITEM_MAP, RARITY_EMOJI, RARITY_LABEL, TYPE_EMOJI,
    get_random_item, format_item_card,
)

# ========== CẤU HÌNH ==========
TOKEN = "MTUwMTE3Mjk5NjEzNDQwODI2Mg.GomExJ.ZHPLehDv_UphuMUE3Q-0g-OBQPeL5JUxgVmiPU"
PREFIX = "!"
STARTING_BALANCE = 1000

# ========== SETUP BOT ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
db = Database("horse_racing.json")

active_races: dict[int, HorseRace] = {}


# ========== EVENTS ==========
@bot.event
async def on_ready():
    print(f"✅ Bot đã sẵn sàng: {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="🐴 Đua Ngựa | !help"
        )
    )
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Đã sync {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Lỗi sync: {e}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Vui lòng chờ **{error.retry_after:.1f}s** trước khi dùng lệnh này!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Thiếu tham số! Dùng `{PREFIX}help` để xem hướng dẫn.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Tham số không hợp lệ!")
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")


# ========== HELPERS ==========
def get_balance(user_id: int) -> int:
    return db.get_balance(str(user_id), STARTING_BALANCE)

def set_balance(user_id: int, amount: int):
    db.set_balance(str(user_id), amount)

def fmt(n) -> str:
    return f"{int(n):,}"


# ══════════════════════════════════════════════════════════════════════════════
#  LỆNH COIN
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="balance", aliases=["bal", "coins", "xu"])
async def balance(ctx, member: Optional[discord.Member] = None):
    target = member or ctx.author
    bal = get_balance(target.id)
    embed = discord.Embed(title="💰 Số Dư Tài Khoản", color=discord.Color.gold())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name=f"👤 {target.display_name}", value=f"🪙 **{fmt(bal)} coin**", inline=False)
    embed.set_footer(text=f"{PREFIX}daily • {PREFIX}inventory • {PREFIX}lbclaim")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  LỆNH DAILY — 25% cơ hội nhận đạo cụ
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Nhận coin hàng ngày. 25% cơ hội nhận thêm 1 đạo cụ ngẫu nhiên."""
    uid = str(ctx.author.id)
    reward = random.randint(200, 500)
    bal = get_balance(ctx.author.id)
    new_bal = bal + reward
    set_balance(ctx.author.id, new_bal)

    embed = discord.Embed(
        title="🎁 Coin Hàng Ngày",
        color=discord.Color.green()
    )
    embed.add_field(name="🪙 Coin nhận được", value=f"**+{fmt(reward)} coin**", inline=True)
    embed.add_field(name="💳 Số dư mới", value=f"**{fmt(new_bal)} coin**", inline=True)

    # 25% cơ hội nhận đạo cụ
    if random.random() < 0.25:
        item = get_random_item()
        db.add_item(uid, item.id, 1)
        r_emoji = RARITY_EMOJI[item.rarity]
        r_label = RARITY_LABEL[item.rarity]
        embed.add_field(
            name="🎲 May Mắn! Nhận được Đạo Cụ",
            value=(
                f"{item.emoji} **{item.name}** {r_emoji} *{r_label}*\n"
                f"_{item.description}_\n"
                f"Dùng `{PREFIX}inventory` để xem túi đồ!"
            ),
            inline=False
        )
        embed.color = discord.Color.purple()
    else:
        embed.add_field(
            name="🎲 Không có đạo cụ hôm nay",
            value="Xác suất 25%. Thử lại ngày mai!",
            inline=False
        )

    embed.set_footer(text="Quay lại sau 24 giờ!")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  LỆNH TÚI ĐỒ
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="inventory", aliases=["inv", "tui", "bag"])
async def inventory(ctx, member: Optional[discord.Member] = None):
    """Xem túi đạo cụ của bạn."""
    target = member or ctx.author
    uid = str(target.id)
    inv = db.get_inventory(uid)
    pending = db.get_lb_items(uid)

    embed = discord.Embed(
        title=f"🎒 Túi Đồ — {target.display_name}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=target.display_avatar.url)

    if not inv:
        embed.description = (
            "Túi trống! Kiếm đạo cụ bằng:\n"
            f"• `{PREFIX}daily` — 25% nhận đạo cụ ngẫu nhiên\n"
            f"• `{PREFIX}lbclaim` — nhận thưởng BXH hàng ngày"
        )
    else:
        lines = []
        for item_id, qty in inv.items():
            item = ITEM_MAP.get(item_id)
            if item:
                lines.append(format_item_card(item, qty))
        embed.description = "\n\n".join(lines)

    if pending > 0:
        embed.add_field(
            name="📦 Đạo Cụ BXH Chờ Nhận",
            value=f"Bạn có **{pending}** đạo cụ từ BXH chưa nhận!\nDùng `{PREFIX}lbclaim` để mở ngay.",
            inline=False
        )

    embed.set_footer(text=f"Dùng {PREFIX}useitem <id> <ngựa> để dùng đạo cụ khi đặt cược!")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  LỆNH XEM DANH SÁCH ĐẠO CỤ
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="itemlist", aliases=["items", "shop", "daocu"])
async def item_list(ctx):
    """Xem toàn bộ danh sách đạo cụ trong game."""
    embed = discord.Embed(
        title="📦 Danh Sách Đạo Cụ",
        description="Đạo cụ kiếm được từ `!daily` (25%) và `!lbclaim` (BXH hàng ngày).",
        color=discord.Color.teal()
    )

    boost_lines = []
    debuff_lines = []
    for item in ALL_ITEMS:
        r_emoji = RARITY_EMOJI[item.rarity]
        r_label = RARITY_LABEL[item.rarity]
        dw = f"+{item.win_delta*100:.0f}%" if item.win_delta > 0 else f"{item.win_delta*100:.0f}%"
        dm = f"+×{item.mult_delta:.1f}" if item.mult_delta > 0 else f"×{item.mult_delta:.1f}"
        line = f"{item.emoji} `{item.id}` **{item.name}** {r_emoji}{r_label} — Tỉ lệ `{dw}` | Nhân `{dm}`"
        if item.item_type == "boost":
            boost_lines.append(line)
        else:
            debuff_lines.append(line)

    embed.add_field(
        name="📈 BOOST — Tăng Tỉ Lệ Thắng (giảm nhân)",
        value="\n".join(boost_lines),
        inline=False
    )
    embed.add_field(
        name="📉 DEBUFF — Giảm Tỉ Lệ Thắng (tăng nhân × cao)",
        value="\n".join(debuff_lines),
        inline=False
    )
    embed.add_field(
        name="💡 Cách Dùng",
        value=(
            f"`{PREFIX}useitem <item_id> <số ngựa>` — Áp dụng đạo cụ trước khi cuộc đua bắt đầu\n"
            f"Ví dụ: `{PREFIX}useitem carrot 3` → Tăng tỉ lệ ngựa số 3"
        ),
        inline=False
    )
    embed.set_footer(text="⚪ Thường (65%)  🔵 Hiếm (28%)  🟣 Sử Thi (7%)")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  LỆNH DÙNG ĐẠO CỤ
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="useitem", aliases=["use", "dung"])
async def use_item(ctx, item_id: str, horse_num: int):
    """Dùng đạo cụ lên một con ngựa trong cuộc đua hiện tại."""
    channel_id = ctx.channel.id
    uid = str(ctx.author.id)

    # Kiểm tra cuộc đua
    if channel_id not in active_races:
        await ctx.send(f"❌ Không có cuộc đua nào! Dùng `{PREFIX}race` trước.")
        return

    race = active_races[channel_id]
    if race.is_running:
        await ctx.send("❌ Cuộc đua đã bắt đầu, không thể dùng đạo cụ!")
        return

    # Kiểm tra số ngựa
    if not (1 <= horse_num <= 5):
        await ctx.send("❌ Số ngựa phải từ 1 đến 5!")
        return

    # Kiểm tra item hợp lệ
    item = ITEM_MAP.get(item_id.lower())
    if not item:
        await ctx.send(
            f"❌ Không tìm thấy đạo cụ `{item_id}`!\n"
            f"Dùng `{PREFIX}itemlist` để xem danh sách ID đạo cụ."
        )
        return

    # Kiểm tra có trong túi không
    if not db.has_item(uid, item_id):
        await ctx.send(
            f"❌ Bạn không có **{item.emoji} {item.name}** trong túi!\n"
            f"Kiếm bằng `{PREFIX}daily` hoặc `{PREFIX}lbclaim`."
        )
        return

    horse = race.horses[horse_num - 1]

    # Lấy tỉ lệ TRƯỚC khi áp item (để hiển thị delta)
    wr_before = horse.win_rate
    mult_before = horse.multiplier

    # Áp dụng item (cộng dồn)
    db.remove_item(uid, item_id, 1)
    race.apply_item(horse_num - 1, item, uid)

    horse = race.horses[horse_num - 1]  # sau khi apply
    count = race.get_applied_count(horse_num - 1)

    r_emoji = RARITY_EMOJI[item.rarity]
    t_emoji = TYPE_EMOJI[item.item_type]
    dw = f"+{item.win_delta*100:.0f}%" if item.win_delta > 0 else f"{item.win_delta*100:.0f}%"
    dm = f"+×{item.mult_delta:.1f}" if item.mult_delta > 0 else f"×{item.mult_delta:.1f}"

    embed = discord.Embed(
        title="✨ Đạo Cụ Đã Áp Dụng!",
        color=discord.Color.purple() if item.item_type == "boost" else discord.Color.red()
    )
    embed.add_field(name="🎒 Đạo Cụ", value=f"{item.emoji} **{item.name}** {r_emoji}", inline=True)
    embed.add_field(name="🐴 Ngựa", value=f"#{horse_num} {horse.emoji} **{horse.name}**", inline=True)
    embed.add_field(name="👤 Người Dùng", value=ctx.author.display_name, inline=True)
    embed.add_field(
        name=f"{t_emoji} Hiệu Ứng Vừa Thêm",
        value=(
            f"Tỉ lệ: `{wr_before*100:.0f}%` {dw} → **{horse.win_rate*100:.0f}%**\n"
            f"Nhân:  `×{mult_before}` {dm} → **×{horse.multiplier}**"
        ),
        inline=False
    )

    # Hiển thị toàn bộ stack đạo cụ đã cộng dồn lên ngựa này
    stack = race.applied_items.get(horse_num - 1, [])
    if len(stack) > 1:
        stack_lines = []
        for entry in stack:
            it = ITEM_MAP.get(entry["item_id"])
            m = ctx.guild.get_member(int(entry["user_id"]))
            uname = m.display_name if m else f"User#{entry['user_id']}"
            if it:
                dw2 = f"+{it.win_delta*100:.0f}%" if it.win_delta > 0 else f"{it.win_delta*100:.0f}%"
                stack_lines.append(f"{it.emoji} **{it.name}** `{dw2}` — *{uname}*")
        embed.add_field(
            name=f"📚 Tổng Cộng {count} Đạo Cụ Trên Ngựa Này",
            value="\n".join(stack_lines),
            inline=False
        )
        embed.add_field(
            name="📊 Chỉ Số Hiện Tại",
            value=f"Tỉ lệ thắng: **{horse.win_rate*100:.0f}%** | Hệ số nhân: **×{horse.multiplier}**",
            inline=False
        )

    embed.set_footer(text=f"Đặt cược: {PREFIX}bet {horse_num} <số tiền> | Xem đạo cụ: {PREFIX}raceinfo")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  LỆNH RACEINFO — trạng thái ngựa + đạo cụ đang áp dụng
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="raceinfo", aliases=["ri", "horses", "ngua"])
async def race_info(ctx):
    """Xem trạng thái ngựa + toàn bộ đạo cụ đang cộng dồn trong cuộc đua."""
    channel_id = ctx.channel.id
    if channel_id not in active_races:
        await ctx.send(f"❌ Không có cuộc đua nào! Dùng `{PREFIX}race` để bắt đầu.")
        return

    race = active_races[channel_id]
    embed = discord.Embed(
        title="📊 Trạng Thái Cuộc Đua Hiện Tại",
        color=discord.Color.orange()
    )

    for i, horse in enumerate(race.horses):
        stack = race.applied_items.get(i, [])
        base_wr   = horse._base_win_rate
        base_mult = horse._base_multiplier
        wr_diff   = round(horse.win_rate - base_wr, 2)
        mult_diff = round(horse.multiplier - base_mult, 1)

        if wr_diff != 0:
            wr_str = (
                f"{base_wr*100:.0f}% → **{horse.win_rate*100:.0f}%** "
                f"({'▲' if wr_diff > 0 else '▼'}{abs(wr_diff)*100:.0f}%)"
            )
        else:
            wr_str = f"**{horse.win_rate*100:.0f}%**"

        if mult_diff != 0:
            mult_str = (
                f"×{base_mult} → **×{horse.multiplier}** "
                f"({'▲' if mult_diff > 0 else '▼'}×{abs(mult_diff):.1f})"
            )
        else:
            mult_str = f"**×{horse.multiplier}**"

        stats_line = f"Tỉ lệ: {wr_str} | Nhân: {mult_str}"

        if stack:
            item_lines = []
            for entry in stack:
                it = ITEM_MAP.get(entry["item_id"])
                m = ctx.guild.get_member(int(entry["user_id"]))
                uname = m.display_name if m else f"User#{entry['user_id']}"
                if it:
                    dw = f"+{it.win_delta*100:.0f}%" if it.win_delta > 0 else f"{it.win_delta*100:.0f}%"
                    item_lines.append(f"  {it.emoji} {it.name} `{dw}` — *{uname}*")
            field_val = stats_line + "\n" + "\n".join(item_lines)
        else:
            field_val = stats_line + "\n  *(chưa có đạo cụ)*"

        embed.add_field(
            name=f"#{i+1} {horse.emoji} {horse.name}",
            value=field_val,
            inline=False
        )

    embed.set_footer(text=f"{PREFIX}useitem <id> <ngựa> để thêm | {PREFIX}bet để đặt cược")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  BẢNG XẾP HẠNG + NHẬN THƯỞNG ĐẠO CỤ
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="leaderboard", aliases=["lb", "top", "xephang"])
async def leaderboard(ctx):
    """Xem top 10 giàu nhất. Bot tự tính và phân phát đạo cụ BXH."""
    all_data = db.get_all()
    sorted_data = sorted(all_data.items(), key=lambda x: x[1], reverse=True)[:10]

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    # Số đạo cụ BXH theo hạng: top1=4, top2=3, top3=2, còn lại=1
    lb_rewards = {0: 4, 1: 3, 2: 2}

    embed = discord.Embed(title="🏆 Bảng Xếp Hạng Coin", color=discord.Color.gold())
    board_text = ""
    for i, (uid, bal) in enumerate(sorted_data):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User#{uid}"
        reward = lb_rewards.get(i, 1)
        board_text += f"{medals[i]} **{name}**: {fmt(bal)} coin — +**{reward}** 📦 đạo cụ\n"

        # Tích lũy phần thưởng
        db.add_lb_items(uid, reward)

    embed.description = board_text or "Chưa có dữ liệu!"
    embed.add_field(
        name="📦 Nhận Thưởng Đạo Cụ",
        value=(
            "Đạo cụ đã được thêm vào hàng chờ!\n"
            f"Dùng `{PREFIX}lbclaim` để mở thành đạo cụ ngẫu nhiên."
        ),
        inline=False
    )
    embed.add_field(
        name="🎁 Phần Thưởng BXH",
        value="🥇 Top 1: **4 đạo cụ** | 🥈 Top 2: **3 đạo cụ** | 🥉 Top 3: **2 đạo cụ** | 🏅 Còn lại: **1 đạo cụ**",
        inline=False
    )
    embed.set_footer(text=f"{PREFIX}lbclaim để nhận đạo cụ!")
    await ctx.send(embed=embed)


@bot.command(name="lbclaim", aliases=["claim", "nhanqua"])
async def lb_claim(ctx):
    """Mở đạo cụ BXH đang chờ nhận."""
    uid = str(ctx.author.id)
    pending = db.get_lb_items(uid)

    if pending <= 0:
        await ctx.send(
            f"❌ Bạn không có đạo cụ BXH nào chờ nhận!\n"
            f"Xem bảng xếp hạng bằng `{PREFIX}leaderboard` để nhận thưởng."
        )
        return

    # Mở từng đạo cụ
    received = []
    for _ in range(pending):
        item = get_random_item()
        db.add_item(uid, item.id, 1)
        received.append(item)

    db.clear_lb_items(uid)

    embed = discord.Embed(
        title=f"🎁 Nhận {pending} Đạo Cụ BXH!",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    lines = []
    for item in received:
        r_emoji = RARITY_EMOJI[item.rarity]
        r_label = RARITY_LABEL[item.rarity]
        lines.append(f"{item.emoji} **{item.name}** {r_emoji}*{r_label}*")

    embed.description = "\n".join(lines)
    embed.add_field(
        name="🎒 Túi Đồ",
        value=f"Dùng `{PREFIX}inventory` để xem toàn bộ đạo cụ!",
        inline=False
    )
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  CUỘC ĐUA
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="race", aliases=["dua", "start"])
@commands.cooldown(1, 30, commands.BucketType.channel)
async def start_race(ctx):
    """Bắt đầu cuộc đua ngựa mới."""
    channel_id = ctx.channel.id
    if channel_id in active_races:
        await ctx.send("⚠️ Đang có cuộc đua trong kênh này!")
        return

    race = HorseRace()
    active_races[channel_id] = race

    embed = discord.Embed(
        title="🏇 CUỘC ĐUA NGỰA BẮT ĐẦU!",
        description="**Đặt cược ngay!** Cuộc đua bắt đầu sau **30 giây**",
        color=discord.Color.orange()
    )

    horses_info = ""
    for i, horse in enumerate(race.horses, 1):
        bar = "▓" * int(horse.win_rate * 10) + "░" * (10 - int(horse.win_rate * 10))
        horses_info += (
            f"{horse.emoji} **#{i} {horse.name}**\n"
            f"   💰 Tỉ lệ: **{horse.win_rate*100:.0f}%** | Nhân: **×{horse.multiplier}**\n"
            f"   {bar}\n\n"
        )

    embed.add_field(name="🐴 Danh Sách Ngựa", value=horses_info, inline=False)
    embed.add_field(
        name="📝 Lệnh",
        value=(
            f"`{PREFIX}bet <ngựa> <tiền>` — Đặt cược\n"
            f"`{PREFIX}useitem <item_id> <ngựa>` — Dùng đạo cụ\n"
            f"`{PREFIX}itemlist` — Xem ID đạo cụ"
        ),
        inline=False
    )
    embed.set_footer(text="⏰ 30 giây để đặt cược và dùng đạo cụ!")
    await ctx.send(embed=embed)

    await asyncio.sleep(25)
    if channel_id not in active_races:
        return
    await ctx.send("⚠️ **Còn 5 giây! Đặt cược và dùng đạo cụ ngay!**")
    await asyncio.sleep(5)
    if channel_id not in active_races:
        return

    await run_race(ctx, race)


@bot.command(name="bet", aliases=["dat", "cuoc"])
async def place_bet(ctx, horse_num: int, amount: int):
    """Đặt cược vào một con ngựa."""
    channel_id = ctx.channel.id
    user_id = ctx.author.id

    if channel_id not in active_races:
        await ctx.send(f"❌ Không có cuộc đua nào! Dùng `{PREFIX}race` để bắt đầu.")
        return
    race = active_races[channel_id]
    if race.is_running:
        await ctx.send("❌ Cuộc đua đã bắt đầu!")
        return
    if not (1 <= horse_num <= 5):
        await ctx.send("❌ Số ngựa phải từ 1 đến 5!")
        return
    if amount < 10:
        await ctx.send("❌ Cược tối thiểu là **10 coin**!")
        return

    bal = get_balance(user_id)
    if amount > bal:
        await ctx.send(f"❌ Không đủ coin! Số dư: **{fmt(bal)} coin**")
        return
    if str(user_id) in race.bets:
        old = race.bets[str(user_id)]
        oh = race.horses[old['horse'] - 1]
        await ctx.send(
            f"⚠️ Bạn đã cược **{fmt(old['amount'])} coin** vào #{old['horse']} {oh.name}!\n"
            f"Dùng `{PREFIX}cancelbet` để hủy."
        )
        return

    horse = race.horses[horse_num - 1]
    race.add_bet(str(user_id), horse_num, amount)
    set_balance(user_id, bal - amount)

    embed = discord.Embed(title="✅ Đặt Cược Thành Công!", color=discord.Color.green())
    embed.add_field(name="👤 Người chơi", value=ctx.author.display_name, inline=True)
    embed.add_field(name="🐴 Ngựa", value=f"#{horse_num} {horse.emoji} {horse.name}", inline=True)
    embed.add_field(name="💰 Tiền cược", value=f"{fmt(amount)} coin", inline=True)
    embed.add_field(
        name="🎯 Nếu thắng",
        value=f"**{fmt(int(amount * horse.multiplier))} coin** (×{horse.multiplier})",
        inline=True
    )
    embed.add_field(name="💳 Còn lại", value=f"{fmt(bal - amount)} coin", inline=True)

    # Hiển thị đạo cụ đang áp dụng lên ngựa này (nếu có)
    stack = race.applied_items.get(horse_num - 1, [])
    if stack:
        item_lines = []
        for entry in stack:
            it = ITEM_MAP.get(entry["item_id"])
            if it:
                dw = f"+{it.win_delta*100:.0f}%" if it.win_delta > 0 else f"{it.win_delta*100:.0f}%"
                item_lines.append(f"{it.emoji} {it.name} `{dw}`")
        embed.add_field(
            name=f"✨ {len(stack)} Đạo Cụ Trên Ngựa Này",
            value=" | ".join(item_lines) + f"\nTỉ lệ thắng hiện tại: **{horse.win_rate*100:.0f}%**",
            inline=False
        )
    await ctx.send(embed=embed)


@bot.command(name="cancelbet", aliases=["huy", "cancel"])
async def cancel_bet(ctx):
    channel_id = ctx.channel.id
    uid = str(ctx.author.id)
    if channel_id not in active_races:
        await ctx.send("❌ Không có cuộc đua nào!")
        return
    race = active_races[channel_id]
    if race.is_running:
        await ctx.send("❌ Cuộc đua đã bắt đầu!")
        return
    if uid not in race.bets:
        await ctx.send("❌ Bạn chưa đặt cược!")
        return
    bet = race.bets.pop(uid)
    bal = get_balance(ctx.author.id)
    set_balance(ctx.author.id, bal + bet['amount'])
    await ctx.send(f"✅ Đã hủy và hoàn **{fmt(bet['amount'])} coin** cho **{ctx.author.display_name}**!")


# ══════════════════════════════════════════════════════════════════════════════
#  HÀM CHẠY ĐUA
# ══════════════════════════════════════════════════════════════════════════════

async def run_race(ctx, race: HorseRace):
    channel_id = ctx.channel.id
    race.is_running = True

    # Hiển thị trạng thái đạo cụ trước khi chạy (hỗ trợ cộng dồn nhiều item/ngựa)
    if race.applied_items:
        pre_embed = discord.Embed(
            title="✨ Đạo Cụ Đã Áp Dụng Trước Giờ Đua",
            color=discord.Color.purple()
        )
        for idx, stack in race.applied_items.items():
            h = race.horses[idx]
            lines = []
            for entry in stack:
                it = ITEM_MAP.get(entry["item_id"])
                m = ctx.guild.get_member(int(entry["user_id"]))
                uname = m.display_name if m else "Ai đó"
                if it:
                    dw = f"+{it.win_delta*100:.0f}%" if it.win_delta > 0 else f"{it.win_delta*100:.0f}%"
                    lines.append(f"{it.emoji} **{it.name}** `{dw}` — *{uname}*")
            pre_embed.add_field(
                name=f"#{idx+1} {h.emoji} {h.name} — {len(stack)} đạo cụ | Tỉ lệ: {h.win_rate*100:.0f}% | ×{h.multiplier}",
                value="\n".join(lines) or "—",
                inline=False
            )
        await ctx.send(embed=pre_embed)
        await asyncio.sleep(1)

    await ctx.send("🚦 **XUẤT PHÁT!** 🏇💨")
    await asyncio.sleep(1)

    track_length = 20
    winner_idx = race.determine_winner()

    # Tạo bước chạy
    steps = []
    for step in range(track_length):
        pos = []
        for i in range(5):
            if i == winner_idx:
                progress = (step + 1) / track_length
                pos.append(track_length if step == track_length - 1
                            else int(progress * track_length * random.uniform(0.85, 1.0)))
            else:
                max_pos = track_length - 1 if step == track_length - 1 else step + 1
                pos.append(random.randint(max(0, step - 3), min(max_pos, step + 1)))
        steps.append(pos)

    msg = None
    for update_num in range(3):
        step_idx = (update_num + 1) * (track_length // 3) - 1
        current_pos = steps[step_idx]

        track_display = ""
        for i, horse in enumerate(race.horses):
            p = current_pos[i]
            # Hiển thị icon đạo cụ trên ngựa nếu có
            has_item = bool(race.applied_items.get(i))
            suffix = " ✨" if has_item else ""
            track = "─" * p + horse.emoji + "─" * (track_length - p)
            track_display += f"`|{track}🏁|` #{i+1} {horse.name}{suffix}\n"

        embed = discord.Embed(
            title=f"🏇 ĐANG ĐUA... {'🔥' * (update_num + 1)}",
            description=track_display,
            color=discord.Color.orange()
        )
        if msg is None:
            msg = await ctx.send(embed=embed)
        else:
            await msg.edit(embed=embed)
        await asyncio.sleep(2)

    # Kết quả
    winner_horse = race.horses[winner_idx]
    final_display = ""
    for i, horse in enumerate(race.horses):
        if i == winner_idx:
            track = "─" * track_length + horse.emoji
        else:
            p = random.randint(track_length - 5, track_length - 1)
            track = "─" * p + horse.emoji + "─" * (track_length - p)
        final_display += f"`|{track}🏁|` #{i+1} {horse.name}\n"

    embed = discord.Embed(title="🏆 KẾT QUẢ CUỘC ĐUA!", description=final_display, color=discord.Color.gold())
    embed.add_field(
        name="🥇 Ngựa Thắng",
        value=(
            f"{winner_horse.emoji} **#{winner_idx+1} {winner_horse.name}**\n"
            f"Nhân: ×{winner_horse.multiplier} | Tỉ lệ: {winner_horse.win_rate*100:.0f}%"
        ),
        inline=False
    )

    winners_text = ""
    losers_text = ""
    for uid, bet_info in race.bets.items():
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User#{uid}"
        amount = bet_info['amount']
        if bet_info['horse'] - 1 == winner_idx:
            winnings = int(amount * winner_horse.multiplier)
            set_balance(int(uid), get_balance(int(uid)) + winnings)
            profit = winnings - amount
            winners_text += f"🎉 **{name}**: +{fmt(profit)} coin (nhận {fmt(winnings)} coin)\n"
        else:
            losers_text += f"💸 **{name}**: -{fmt(amount)} coin\n"

    if winners_text:
        embed.add_field(name="🎉 Người Thắng", value=winners_text, inline=False)
    if losers_text:
        embed.add_field(name="💸 Người Thua", value=losers_text, inline=False)
    if not winners_text and not losers_text:
        embed.add_field(name="😶 Không Ai Đặt Cược", value="Không có ai tham gia!", inline=False)

    embed.set_footer(text=f"{PREFIX}race để đua tiếp | {PREFIX}inventory xem đạo cụ")
    if msg:
        await msg.edit(embed=embed)
    else:
        await ctx.send(embed=embed)

    if channel_id in active_races:
        del active_races[channel_id]


# ══════════════════════════════════════════════════════════════════════════════
#  HELP
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="help", aliases=["huongdan", "h"])
async def help_command(ctx):
    embed = discord.Embed(
        title="🐴 Bot Đua Ngựa — Hướng Dẫn",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🎮 Đua Ngựa",
        value=(
            f"`{PREFIX}race` — Bắt đầu cuộc đua\n"
            f"`{PREFIX}bet <ngựa> <tiền>` — Đặt cược\n"
            f"`{PREFIX}useitem <id> <ngựa>` — Dùng đạo cụ\n"
            f"`{PREFIX}cancelbet` — Hủy cược"
        ),
        inline=False
    )
    embed.add_field(
        name="🎒 Đạo Cụ",
        value=(
            f"`{PREFIX}itemlist` — Xem tất cả đạo cụ\n"
            f"`{PREFIX}inventory` — Xem túi đồ của bạn\n"
            f"`{PREFIX}lbclaim` — Nhận đạo cụ từ BXH"
        ),
        inline=False
    )
    embed.add_field(
        name="💰 Coin",
        value=(
            f"`{PREFIX}balance [@user]` — Xem số dư\n"
            f"`{PREFIX}daily` — Nhận coin + 25% đạo cụ\n"
            f"`{PREFIX}leaderboard` — BXH + phân phát đạo cụ"
        ),
        inline=False
    )
    embed.add_field(
        name="📦 Cách Nhận Đạo Cụ",
        value=(
            "• **`!daily`** → 25% cơ hội nhận 1 đạo cụ ngẫu nhiên\n"
            "• **`!leaderboard`** → Mỗi ngày: Top1=4, Top2=3, Top3=2, Còn lại=1 đạo cụ\n"
            "• Sau đó dùng **`!lbclaim`** để mở thành đạo cụ cụ thể"
        ),
        inline=False
    )
    embed.add_field(
        name="📊 Hiệu Ứng Đạo Cụ",
        value=(
            "📈 **BOOST** — Tăng tỉ lệ thắng ngựa, giảm nhân tiền\n"
            "📉 **DEBUFF** — Giảm tỉ lệ thắng ngựa, tăng nhân tiền (rủi ro cao, thưởng lớn!)"
        ),
        inline=False
    )
    embed.set_footer(text="⚪ Thường (65%)  🔵 Hiếm (28%)  🟣 Sử Thi (7%) — Chúc may mắn! 🍀")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    bot.run(TOKEN)

token = os.getenv('DISCORD_TOKEN')
client.run(token)
