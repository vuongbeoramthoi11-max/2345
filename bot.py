# bot3.py - selfbot Discord sử dụng discord.py-self
# Yêu cầu: pip install -U discord.py-self
# OWNER và CO_OWNER có toàn quyền, ADMIN dùng say/ngon

import asyncio
import random
from pathlib import Path

import discord
from discord.ext import commands

BASE_DIR = Path(__file__).resolve().parent
NGON_FILE = BASE_DIR / "ngon_da_them_hash.txt"

TOKEN = "MTQxNzQ5NzY2NzQ0OTEyNjk1Mg.GeoPzX.IxyVtEZ9dbNOQDJ34PXvIrpKS8XM61lj6o-JEs"

MIN_INTERVAL = 0.1
TREO_MIN_INTERVAL = 1.0

# OWNER có toàn quyền
OWNER_ID = 1417497667449126952

# CO_OWNER có toàn quyền
CO_OWNER_ID = 1330425526363623494

# ADMIN_IDS dùng được startsay, stopsay, startngon, stopngon
ADMIN_IDS = {
    OWNER_ID,
    CO_OWNER_ID,
}

loop_tasks = {}
ngon_tasks = {}
treo_tasks = {}
ngon_queues = {}


def load_ngon():
    # Đọc danh sách dòng từ file ngôn
    try:
        if not NGON_FILE.exists():
            print(f"[NGON] KHÔNG TÌM THẤY: {NGON_FILE}")
            return []

        with NGON_FILE.open("r", encoding="utf-8-sig") as f:
            lines = [line.strip() for line in f if line.strip()]

        print(f"[NGON] Đã đọc được {len(lines)} dòng")
        return lines

    except Exception as e:
        print(f"[NGON] Lỗi: {e}")
        return []


def get_next_ngon(channel_id):
    # Lấy dòng tiếp theo trong hàng đợi ngôn cho channel
    queue = ngon_queues.get(channel_id)

    if not queue:
        data = load_ngon()
        if not data:
            return None

        queue = data.copy()
        random.shuffle(queue)
        ngon_queues[channel_id] = queue

    return queue.pop()


def is_owner(user_id):
    # OWNER hoặc CO_OWNER dùng mọi lệnh
    return user_id in {OWNER_ID, CO_OWNER_ID}


def is_admin(user_id):
    # ADMIN_IDS dùng startsay, stopsay, startngon, stopngon
    return user_id in ADMIN_IDS


# Khởi tạo selfbot
bot = commands.Bot(command_prefix="!", self_bot=True)


@bot.event
async def on_ready():
    # In thông tin khi selfbot khởi động
    print("=" * 45)
    print(f"🤖 Selfbot: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌍 Đã tham gia {len(bot.guilds)} server")
    print("=" * 45)

    for i, guild in enumerate(bot.guilds, start=1):
        print(f"{i}. {guild.name} ({guild.id})")


@bot.command(name="addadmin")
async def addadmin(ctx, user_id: int):
    # Chỉ OWNER hoặc CO_OWNER được thêm admin
    if not is_owner(ctx.author.id):
        return

    if user_id in ADMIN_IDS:
        await ctx.send(f"⚠️ ID `{user_id}` đã là admin.", delete_after=5)
        return

    ADMIN_IDS.add(user_id)
    await ctx.send(f"✅ Đã thêm `{user_id}` làm admin.", delete_after=5)


@bot.command(name="removeadmin")
async def removeadmin(ctx, user_id: int):
    # Chỉ OWNER hoặc CO_OWNER được thu quyền admin
    if not is_owner(ctx.author.id):
        return

    if user_id in {OWNER_ID, CO_OWNER_ID}:
        await ctx.send("❌ Không thể xóa quyền OWNER/CO_OWNER.", delete_after=5)
        return

    if user_id not in ADMIN_IDS:
        await ctx.send(f"⚠️ ID `{user_id}` không phải admin.", delete_after=5)
        return

    ADMIN_IDS.remove(user_id)
    await ctx.send(f"✅ Đã xóa quyền admin của `{user_id}`.", delete_after=5)


@bot.command(name="listadmin")
async def listadmin(ctx):
    # Chỉ OWNER hoặc CO_OWNER xem danh sách admin
    if not is_owner(ctx.author.id):
        return

    if not ADMIN_IDS:
        await ctx.send("📋 Không có admin nào.", delete_after=5)
        return

    lines = []
    for uid in sorted(ADMIN_IDS):
        if uid == OWNER_ID:
            tag = " (OWNER)"
        elif uid == CO_OWNER_ID:
            tag = " (CO_OWNER)"
        else:
            tag = ""
        lines.append(f"• `{uid}`{tag}")

    await ctx.send("👑 **Danh sách Admin**\n\n" + "\n".join(lines))


@bot.command(name="servers")
async def servers(ctx):
    # Liệt kê server selfbot đang tham gia
    if not is_owner(ctx.author.id):
        return

    if not bot.guilds:
        await ctx.send("Selfbot chưa ở server nào.", delete_after=5)
        return

    lines = []
    for g in bot.guilds:
        lines.append(f"**{g.name}**\nID: `{g.id}` | Thành viên: {g.member_count}")

    await ctx.send("## 🌍 Danh sách server\n\n" + "\n\n".join(lines))


@bot.command(name="startsay")
async def startsay(ctx, seconds: float, *, message: str):
    # Bật gửi tin nhắn định kỳ trong channel
    if not is_admin(ctx.author.id):
        return

    if seconds < MIN_INTERVAL:
        seconds = MIN_INTERVAL

    channel = ctx.channel
    channel_id = ctx.channel.id

    async def sender():
        # Vòng lặp gửi tin nhắn
        while True:
            try:
                await channel.send(message)
                await asyncio.sleep(seconds)
            except asyncio.CancelledError:
                raise
            except discord.HTTPException as e:
                print(f"[DISCORD ERROR] {e}")
                await asyncio.sleep(seconds)

    loop_tasks.setdefault(channel_id, []).append(asyncio.create_task(sender()))
    await ctx.send(f"✅ Đã bật gửi tin mỗi {seconds:g} giây.", delete_after=5)


@bot.command(name="stopsay")
async def stopsay(ctx):
    # Dừng mọi vòng gửi tin trong channel
    if not is_admin(ctx.author.id):
        return

    channel_id = ctx.channel.id
    tasks_list = loop_tasks.pop(channel_id, None)

    if tasks_list:
        for t in tasks_list:
            t.cancel()
        await ctx.send("✅ Đã tắt tất cả loop trong channel này.", delete_after=5)
    else:
        await ctx.send("ℹ️ Channel này không có loop nào đang chạy.", delete_after=5)


@bot.command(name="startngon")
async def startngon(ctx, seconds: float = MIN_INTERVAL, *, user: discord.User = None):
    # Bắt đầu đọc file ngôn định kỳ
    if not is_admin(ctx.author.id):
        return

    if seconds < MIN_INTERVAL:
        seconds = MIN_INTERVAL

    channel = ctx.channel
    channel_id = ctx.channel.id

    if not load_ngon():
        await ctx.send("❌ File không tồn tại hoặc không có dòng nào.", delete_after=5)
        return

    async def ngon_sender():
        # Vòng lặp gửi từng dòng ngôn
        while True:
            try:
                line = get_next_ngon(channel_id)
                if line is None:
                    await asyncio.sleep(seconds)
                    continue

                content = line
                if user:
                    content += f" {user.mention}"

                await channel.send(content)
                await asyncio.sleep(seconds)

            except asyncio.CancelledError:
                raise
            except discord.HTTPException as e:
                print(f"[NGON DISCORD ERROR] {e}")
                await asyncio.sleep(max(seconds, MIN_INTERVAL))

    ngon_tasks.setdefault(channel_id, []).append(asyncio.create_task(ngon_sender()))

    tag_text = f" và tag {user.mention}" if user else ""
    await ctx.send(f"✅ Đã bắt đầu đọc file mỗi {seconds:g} giây{tag_text}.", delete_after=5)


@bot.command(name="stopngon")
async def stopngon(ctx):
    # Dừng mọi vòng đọc file ngôn trong channel
    if not is_admin(ctx.author.id):
        return

    channel_id = ctx.channel.id
    tasks_list = ngon_tasks.pop(channel_id, None)

    if tasks_list:
        for t in tasks_list:
            t.cancel()
        await ctx.send("✅ Đã dừng tất cả vòng đọc file trong channel này.", delete_after=5)
    else:
        await ctx.send("ℹ️ Channel này không có vòng đọc file nào.", delete_after=5)


@bot.command(name="starttreo")
async def starttreo(ctx, delay: float, noidung: str, bio: str):
    # Bật gửi 9 dòng nội dung kèm link định kỳ
    if not is_owner(ctx.author.id):
        return

    if delay < TREO_MIN_INTERVAL:
        delay = TREO_MIN_INTERVAL

    channel = ctx.channel
    noidung = noidung.strip()
    bio = bio.strip()

    if not bio.startswith(("http://", "https://")):
        bio = "https://" + bio

    message = "\n".join([f"# > [ {noidung}](<{bio}>)" ] * 9)

    async def treo_loop():
        # Vòng lặp gửi nội dung treo
        while True:
            try:
                await channel.send(message)
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                raise
            except discord.HTTPException:
                await asyncio.sleep(delay)

    treo_tasks.setdefault(ctx.channel.id, []).append(asyncio.create_task(treo_loop()))
    await ctx.send(f"✅ Đã bật gửi mỗi {delay:g} giây.", delete_after=5)


@bot.command(name="stoptreo")
async def stoptreo(ctx):
    # Dừng toàn bộ vòng treo trong channel
    if not is_owner(ctx.author.id):
        return

    tasks = treo_tasks.pop(ctx.channel.id, None)
    if tasks:
        for t in tasks:
            t.cancel()
        await ctx.send("✅ Đã dừng.", delete_after=5)
    else:
        await ctx.send("ℹ️ Không có vòng nào đang chạy.", delete_after=5)


print("=== TEST FILE NGON ===")
print("Đường dẫn:", NGON_FILE)
print("Tồn tại:", NGON_FILE.exists())
data = load_ngon()
print("Số dòng:", len(data))
print("======================")

bot.run(TOKEN)