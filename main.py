import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import json
import os
import asyncio

# إعداد البوت مع تقليل الـ privileged intents المطلوبة
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
# تفعيل message_content للأوامر النصية (!setup, !check) - اختياري
# intents.message_content = True  # ملاحظة: يحتاج تفعيل في Discord Developer Portal
# intents.members = True  # اختياري - يحسن الأداء لكن ليس ضروري

# ملاحظة: إذا لم تعمل الأوامر النصية (!setup, !check)، فعّل message_content intent في Developer Portal

bot = commands.Bot(command_prefix="!", intents=intents)

# الإعدادات الأساسية
BASE_URL = "https://crimsonscans.site/"
DATA_FILE = "known_releases.json"
ROLE_MSG_FILE = "role_message.json"
GUILD_CONFIG_FILE = "guild_config.json"

# تحميل البيانات السابقة
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        known_releases = json.load(f)
else:
    known_releases = {}

if os.path.exists(ROLE_MSG_FILE):
    with open(ROLE_MSG_FILE, "r", encoding="utf-8") as f:
        role_message = json.load(f)
else:
    role_message = {}  # {guild_id: {"message_id": id, "roles": {emoji: role_name}}}

# تحميل إعدادات الخوادم
if os.path.exists(GUILD_CONFIG_FILE):
    with open(GUILD_CONFIG_FILE, "r", encoding="utf-8") as f:
        guild_configs = json.load(f)
else:
    guild_configs = {}  # {guild_id: {"channel_id": id}}

# قائمة إيموجي ثابتة لجميع الأعمال
EMOJI_LIST = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

def save_data():
    """حفظ بيانات الإصدارات المعروفة"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(known_releases, f, ensure_ascii=False, indent=4)

def save_role_msg():
    """حفظ بيانات رسالة الأدوار"""
    with open(ROLE_MSG_FILE, "w", encoding="utf-8") as f:
        json.dump(role_message, f, ensure_ascii=False, indent=4)

def save_guild_config():
    """حفظ إعدادات الخوادم"""
    with open(GUILD_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(guild_configs, f, ensure_ascii=False, indent=4)

def get_latest_releases():
    """جلب آخر الإصدارات من موقع crimsonscans"""
    try:
        response = requests.get(BASE_URL, timeout=10)
        if response.status_code != 200:
            print(f"خطأ في الاتصال بالموقع: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        latest_section = soup.find("section", {"class": "last-release-home"})
        if not latest_section:
            print("لم يتم العثور على قسم آخر الإصدارات")
            return []
        
        releases = []
        items = latest_section.find_all("li")
        for item in items:
            try:
                link_tag = item.find("a")
                if not link_tag:
                    continue
                
                link = link_tag.get("href", "")
                if link and not link.startswith("http"):
                    link = BASE_URL.rstrip("/") + "/" + link.lstrip("/")
                
                title_tag = item.find("h3")
                title = title_tag.text.strip() if title_tag else "بدون عنوان"
                
                chapter_tag = item.find("span", {"class": "chapter"})
                chapter = chapter_tag.text.strip() if chapter_tag else "بدون رقم"
                
                img_tag = item.find("img")
                img_url = None
                if img_tag:
                    img_url = img_tag.get("data-src") or img_tag.get("src")
                
                if link and title:
                    releases.append({
                        "title": title,
                        "chapter": chapter,
                        "link": link,
                        "img": img_url
                    })
            except Exception as item_error:
                print(f"خطأ في معالجة عنصر: {item_error}")
                continue
        
        return releases
    except Exception as e:
        print(f"خطأ في جلب الإصدارات: {e}")
        return []

async def create_roles_if_not_exist(guild, release_title):
    """إنشاء الأدوار إذا لم تكن موجودة"""
    # رول All Series
    all_series_role = discord.utils.get(guild.roles, name="All Series")
    if not all_series_role:
        all_series_role = await guild.create_role(name="All Series", color=discord.Color.blue())
    
    # رول باسم العمل
    work_role = discord.utils.get(guild.roles, name=release_title)
    if not work_role:
        work_role = await guild.create_role(name=release_title, color=discord.Color.green())
    
    return all_series_role, work_role

async def setup_role_message(channel, guild):
    """إعداد رسالة الأدوار التفاعلية"""
    try:
        # إنشاء رول "All Series" إذا لم يكن موجوداً
        all_series_role = discord.utils.get(guild.roles, name="All Series")
        if not all_series_role:
            all_series_role = await guild.create_role(name="All Series", color=discord.Color.blue())
            print(f"تم إنشاء رول 'All Series' في {guild.name}")
        
        releases = get_latest_releases()
        if not releases:
            return
            
        embed = discord.Embed(
            title="🎭 تفاعل مع رولات الأعمال",
            description="اضغط على الإيموجي للاشتراك/إلغاء الاشتراك في رول العمل المفضل لديك",
            color=discord.Color.blue()
        )

        # استخدم نفس الإيموجي لكل عمل ثابت
        role_mapping = role_message.get(str(guild.id), {}).get("roles", {})

        # إضافة أعمال جديدة بدون تغيير الإيموجي للأعمال القديمة
        existing_titles = set(role_mapping.values())
        available_emojis = [emoji for emoji in EMOJI_LIST if emoji not in role_mapping]
        
        for release in releases:
            if release["title"] not in existing_titles and available_emojis:
                emoji = available_emojis.pop(0)
                role_mapping[emoji] = release["title"]

        # إنشاء جميع الأدوار الموجودة في الخريطة
        for emoji, role_name in role_mapping.items():
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if not existing_role:
                await guild.create_role(name=role_name, color=discord.Color.green())
                print(f"تم إنشاء رول '{role_name}' في {guild.name}")

        # تحديث الـ embed
        for emoji, role_name in list(role_mapping.items())[:10]:  # أقصى 10 أعمال
            embed.add_field(name=f"{emoji} {role_name}", value="اضغط للاشتراك", inline=False)

        # إرسال أو تحديث رسالة الرولات
        msg_id = role_message.get(str(guild.id), {}).get("message_id")
        msg = None
        
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed)
            except discord.NotFound:
                msg = None
            except Exception as e:
                print(f"خطأ في تحديث الرسالة: {e}")
                msg = None

        if not msg:
            msg = await channel.send(embed=embed)
            if msg:
                role_message[str(guild.id)] = {"message_id": msg.id, "roles": role_mapping}
        else:
            role_message[str(guild.id)]["roles"] = role_mapping

        # إضافة الإيموجي
        for emoji in role_mapping:
            try:
                await msg.add_reaction(emoji)
            except Exception as e:
                print(f"خطأ في إضافة تفاعل {emoji}: {e}")

        save_role_msg()
    except Exception as e:
        print(f"خطأ في إعداد رسالة الأدوار: {e}")

@bot.event
async def on_raw_reaction_add(payload):
    """التعامل مع إضافة التفاعلات"""
    if payload.user_id == bot.user.id:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    data = role_message.get(str(guild.id))
    if not data or payload.message_id != data["message_id"]:
        return

    # محاولة الحصول على العضو مع fallback
    member = guild.get_member(payload.user_id)
    if not member:
        try:
            # إذا فشل get_member، نحاول fetch_member كـ fallback
            member = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            print(f"لم يتم العثور على العضو بالمعرف: {payload.user_id}")
            return
        except discord.HTTPException as e:
            print(f"خطأ في جلب العضو: {e}")
            return
        except Exception as e:
            print(f"خطأ غير متوقع في جلب العضو: {e}")
            return
    
    if not member:
        return

    role_name = data["roles"].get(str(payload.emoji))
    if not role_name:
        return

    try:
        role = discord.utils.get(guild.roles, name=role_name)
        # إنشاء الرول إذا لم يكن موجوداً
        if not role:
            role = await guild.create_role(name=role_name, color=discord.Color.green())
            print(f"تم إنشاء رول '{role_name}' عند التفاعل في {guild.name}")
        
        if role and role not in member.roles:
            await member.add_roles(role)
            print(f"تم إضافة رول {role_name} للعضو {member.display_name}")
    except discord.Forbidden:
        print(f"البوت لا يملك صلاحية إضافة/إنشاء الرول {role_name}")
    except discord.HTTPException as e:
        print(f"خطأ HTTP في إضافة الرول: {e}")
    except Exception as e:
        print(f"خطأ في إضافة الرول: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    """التعامل مع إزالة التفاعلات"""
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    data = role_message.get(str(guild.id))
    if not data or payload.message_id != data["message_id"]:
        return

    # محاولة الحصول على العضو مع fallback
    member = guild.get_member(payload.user_id)
    if not member:
        try:
            # إذا فشل get_member، نحاول fetch_member كـ fallback
            member = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            print(f"لم يتم العثور على العضو بالمعرف: {payload.user_id}")
            return
        except discord.HTTPException as e:
            print(f"خطأ في جلب العضو: {e}")
            return
        except Exception as e:
            print(f"خطأ غير متوقع في جلب العضو: {e}")
            return
    
    if not member:
        return

    role_name = data["roles"].get(str(payload.emoji))
    if not role_name:
        return

    try:
        role = discord.utils.get(guild.roles, name=role_name)
        # إنشاء الرول إذا لم يكن موجوداً (في حال إزالة التفاعل قبل إنشاء الرول)
        if not role:
            role = await guild.create_role(name=role_name, color=discord.Color.green())
            print(f"تم إنشاء رول '{role_name}' عند إزالة التفاعل في {guild.name}")
        
        if role and role in member.roles:
            await member.remove_roles(role)
            print(f"تم إزالة رول {role_name} من العضو {member.display_name}")
    except discord.Forbidden:
        print(f"البوت لا يملك صلاحية إزالة/إنشاء الرول {role_name}")
    except discord.HTTPException as e:
        print(f"خطأ HTTP في إزالة الرول: {e}")
    except Exception as e:
        print(f"خطأ في إزالة الرول: {e}")

@tasks.loop(minutes=3)
async def check_new_releases():
    """فحص الإصدارات الجديدة كل 3 دقائق"""
    global known_releases
    
    releases = get_latest_releases()
    if not releases:
        return
    
    # فحص جميع الخوادم المعدة
    for guild_id, config in guild_configs.items():
        channel_id = config.get("channel_id")
        if not channel_id:
            continue
            
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"لم يتم العثور على القناة بالمعرف: {channel_id} في الخادم: {guild_id}")
            continue
        
        if not hasattr(channel, 'guild') or not channel.guild:
            continue
            
        guild = channel.guild
        new_releases_found = False

        for release in releases:
            last_known = known_releases.get(release["link"])
            if last_known != release["chapter"]:
                known_releases[release["link"]] = release["chapter"]
                new_releases_found = True

                try:
                    all_series_role, work_role = await create_roles_if_not_exist(guild, release["title"])

                    embed = discord.Embed(
                        title=f"📚 {release['title']} - {release['chapter']}",
                        url=release['link'],
                        color=discord.Color.purple(),
                        description=f"فصل جديد متاح الآن!"
                    )
                    
                    if release['img']:
                        embed.set_thumbnail(url=release['img'])
                    
                    embed.add_field(name="العمل", value=release['title'], inline=True)
                    embed.add_field(name="الفصل", value=release['chapter'], inline=True)
                    embed.set_footer(text="Crimson Scans", icon_url="https://crimsonscans.site/favicon.ico")
                    
                    if hasattr(channel, 'send'):
                        await channel.send(f"🔔 {all_series_role.mention} {work_role.mention} - إصدار جديد!", embed=embed)
                    print(f"تم إرسال إشعار للإصدار الجديد: {release['title']} - {release['chapter']} في {guild.name}")
                    
                    # تأخير صغير لتجنب الـ rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"خطأ في إرسال الإشعار في {guild.name}: {e}")
        
        if new_releases_found:
            # تحديث رسالة الرولات للتفاعل
            await setup_role_message(channel, guild)
    
    if any(guild_configs.values()):
        save_data()

@check_new_releases.before_loop
async def before_check_new_releases():
    """انتظار حتى يصبح البوت جاهزاً"""
    await bot.wait_until_ready()

@bot.tree.command(name="setup", description="إعداد البوت لمراقبة الإصدارات الجديدة في هذه القناة")
@app_commands.describe(channel="القناة المراد إرسال الإشعارات فيها (اختياري - افتراضي القناة الحالية)")
async def setup_command(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """أمر إعداد البوت للمشرفين"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ هذا الأمر متاح للمشرفين فقط!", ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    guild_id = str(interaction.guild.id)
    
    # حفظ إعدادات الخادم
    guild_configs[guild_id] = {"channel_id": target_channel.id}
    save_guild_config()
    
    embed = discord.Embed(
        title="✅ تم إعداد البوت بنجاح",
        description=f"سيتم إرسال إشعارات الإصدارات الجديدة في هذه القناة: {target_channel.mention}",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)
    await setup_role_message(target_channel, interaction.guild)

@bot.tree.command(name="check", description="فحص يدوي للإصدارات الجديدة من الموقع")
async def manual_check(interaction: discord.Interaction):
    """فحص يدوي للإصدارات الجديدة"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ هذا الأمر متاح للمشرفين فقط!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔍 جاري فحص الإصدارات الجديدة...",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)
    
    releases = get_latest_releases()
    if releases:
        embed = discord.Embed(
            title="📚 تم العثور على الإصدارات التالية:",
            color=discord.Color.green()
        )
        
        for i, release in enumerate(releases[:5], 1):
            embed.add_field(
                name=f"{i}. {release['title']}",
                value=f"الفصل: {release['chapter']}",
                inline=False
            )
        
        await interaction.edit_original_response(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ لم يتم العثور على إصدارات",
            description="قد يكون هناك مشكلة في الاتصال بالموقع",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed)

@bot.event
async def on_ready():
    """عند جهوزية البوت"""
    print(f"🤖 البوت جاهز كـ {bot.user}")
    print(f"📊 متصل بـ {len(bot.guilds)} خادم/خوادم")
    
    # مزامنة slash commands
    try:
        synced = await bot.tree.sync()
        print(f"🔄 تم مزامنة {len(synced)} أمر slash")
    except Exception as e:
        print(f"❌ خطأ في مزامنة الأوامر: {e}")
    
    # بدء فحص الإصدارات
    if not check_new_releases.is_running():
        check_new_releases.start()
        print("✅ تم بدء فحص الإصدارات الجديدة")

# تشغيل البوت
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
        print("يرجى إضافة توكن البوت في متغيرات البيئة")
    else:
        try:
            bot.run(token)
        except Exception as e:
            print(f"❌ خطأ في تشغيل البوت: {e}")