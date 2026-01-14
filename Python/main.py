from highrise import BaseBot, User
from highrise.models import Position, CurrencyItem, Item, AnchorPosition
import random
import asyncio
from sqlitedict import SqliteDict
import os

# إعداد عميل OpenAI باستخدام تكامل Replit
# التكاليف يتم خصمها من رصيدك في Replit.
import openai as openai_legacy

# ضبط الإعدادات للنسخة القديمة من OpenAI (0.28)
openai_legacy.api_base = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
openai_legacy.api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")


class WelcomeBot(BaseBot):
    """بوت ترحيب للاعبين الجدد في Highrise مع ميزات متقدمة"""

    def __init__(self):
        super().__init__()
        # نظام الطابور لمعالجة الرسائل بالترتيب
        self.message_queue = asyncio.Queue()

        # حالة السماح بأمر "بلعب" للجميع (يتم تفعيله عبر !give)
        self.play_command_enabled = False

        # مهمة التذكير المستمر (لأمر !sm)
        self.sm_reminder_task = None

        # قاعدة بيانات لحفظ المشرفين بشكل دائم
        self.db = SqliteDict('./moderators.sqlite', autocommit=True)
        # قاعدة بيانات جديدة للوق الشات
        self.chat_db = SqliteDict('./chat_logs.sqlite', autocommit=True)
        if 'logs' not in self.chat_db:
            self.chat_db['logs'] = []

        # قاعدة بيانات للأوامر المرسلة من الموقع
        self.cmd_db = SqliteDict('./web_commands.sqlite', autocommit=True)
        if 'queue' not in self.cmd_db:
            self.cmd_db['queue'] = []

        # تحميل المشرفين من قاعدة البيانات أو إنشاء قائمة فارغة
        if 'mods' not in self.db:
            self.db['mods'] = []

        self.added_moderators = set(self.db['mods'])

        # معرف صاحب البوت
        self.owner_id = None  # سيتم تحديثه عند بدء الجلسة إذا لزم الأمر، لكننا نعتمد على اسم المستخدم _7rbi

        # اسم البوت للذكاء الاصطناعي
        self.ai_name = "عبنود"

        # قائمة رسائل الترحيب
        self.welcome_messages = [
            "أهلًا وسهلًا بك {} في هذا المكان، سعدنا كثيرًا بانضمامك لنا، نتمنى أن تجد هنا ما يرضيك",
            "سعدنا بوجودك معنا {} ونتمنى لك وقتًا ممتعًا وتجربة جميلة 🤍",
            "مرحبًا بك {} بيننا، وجودك يشرفنا ونتمنى لك أوقات مليئة بالراحة والتفاعل ",
            "حياك الله {} بيننا", "سعدنا بانضمامك لنا {}",
            "مرحبًا بك {}، وجودك إضافة جميلة ونتمنى لك وقتًا طيبًا معنا 🌟"
        ]
        self.welcome_index = 0  # مؤشر للرسالة الحالية لضمان الترتيب
        # ديكشنري لتخزين الرقصات
        self.emotes = {
            "1": "emote-ghost-idle",
            "2": "idle-floorsleeping",
            "3": "idle_layingdown",
            "4": "emote-kissing",
            "5": "idle-uwu",
            "6": "sit-open",
            "ريست": "sit-open",
            "7": "idle-floorsleeping2",
            "8": "idle-floating",
            "9": "emote-shy2",
            "10": "emote-slap",
            "11": "emoji-poop",
            "12": "sit-relaxed",
            "13": "emote-confused",
            "14": "emote-laughing2",
            "15": "dance-pinguin",
            "16": "dance-orangejustice",
            "17": "emote-hyped",
            "ghost": "emote-ghost-idle",
            "sleep": "idle-floorsleeping",
            "lay": "idle_layingdown",
            "kiss": "emote-kissing",
            "uwu": "idle-uwu",
            "sit": "sit-open",
            "sleep2": "idle-floorsleeping2",
            "float": "idle-floating",
            "shy": "emote-shy2",
            "slap": "emote-slap",
            "poop": "emoji-poop",
            "relax": "sit-relaxed",
            "confused": "emote-confused",
            "laugh": "emote-laughing2",
            "penguin": "dance-pinguin",
            "orange": "dance-orangejustice",
            "hyped": "emote-hyped"
        }
        # ديكشنري لتخزين المستخدمين المثبتين ومواقعهم
        self.frozen_users = {}  # user_id: Position
        # تخزين معرف الشخص الذي يتبعه البوت
        self.following_user_id = None
        # قائمة أصحاب البوت (المسموح لهم باستخدام أوامر الإشراف)
        self.bot_owners = ["_7rbi"]  # أضف أسماء المستخدمين هنا
        # قائمة المشرفين المعينين بواسطة البوت (نستخدم أسماء المستخدمين لضمان البقاء)
        self.added_moderators = set(
            self.db['mods'])  # التحميل من قاعدة البيانات
        self.added_moderators_ids = set(
        )  # للسرعة في التحقق أثناء التواجد في الغرفة
        # تخزين المهام الجارية للمرجحة والرقصات اللانهائية
        self.swing_tasks = {}  # user_id: Task
        self.emote_loop_tasks = {}  # user_id: Task
        self.spam_tasks = {}  # user_id: Task
        self.muted_users = set()  # قائمة المستخدمين المكتومين
        # متغيرات لعبة "إنسان، حيوان، نبات..."
        self.game_active = False
        self.game_letter = ""
        self.game_category = ""
        self.game_participants = {}  # user_id: username
        self.game_start_task = None
        self.game_winners = []
        self.game_awaiting_answers = False
        self.game_round = 0
        self.max_rounds = 10
        self.categories = ["إنسان", "حيوان", "نبات", "جماد", "بلاد"]
        self.game_scores = {}  # user_id: points
        self.game_started = False  # لمنع الانضمام بعد البدء

        # قائمة الجمل العشوائية التي يقولها البوت
        self.random_phrases = [
            "نورتوا الغرفة يا جماعة الخير ✨",
            "أحد يبي أسولف معه؟ نادوني عبندي 😉",
            "تذكروا إن الابتسامة ببلاش، ابتسموا! 😊",
            "الغرفة منورة بوجودكم والله 🌟", "يا زين جمعتكم، الله لا يفرقنا 💖",
            "أنا موجود لأي مساعدة، بس نادوا اسمي 🤖", "عاشوا الحاضرين! 👏",
            "وش رايكم نلعب؟ اكتبوا 'لعبة' وخلونا نستمتع 🎮",
            "عبندي في الخدمة دائماً وأبداً 💪", "صلوا على النبي يا جماعة 🤍"
        ]
        self.admin_commands = [
            "🛡️ أوامر المشرفين (جزء 1):\n"
            "• !help - عرض الأوامر (همس)\n"
            "• اتبع @الاسم - البوت يتبع شخصاً\n"
            "• !come - البوت يتبعك\n"
            "• !kick @الاسم - طرد شخص\n"
            "• !ban @الاسم - حظر شخص\n"
            "• !e @الاسم - نسخ ملابس شخص", "🛡️ أوامر المشرفين (جزء 2):\n"
            "• ثبت @الاسم - تجميد حركة شخص\n"
            "• فك @الاسم - فك تجميد شخص\n"
            "• !pull @الاسم - سحب شخص إليك\n"
            "• مرجح @الاسم - مرجحة شخص (قوية)", "🛡️ أوامر المشرفين (جزء 3):\n"
            "• توقيف @الاسم - تثبيت اللاعب في مكانه\n"
            "• out @الاسم - إرسال شخص للخارج\n"
            "• !mute @الاسم [المدة] - كتم شخص\n"
            "• vip [@الاسم] - الانتقال للـ VIP\n"
            "• طلع @الاسم - نقل شخص للخارج",
            "🛡️ أوامر إضافية (للمشرفين فقط):\n"
            "• !go - إعادة البوت لموقعه\n"
            "• !play - انتقال لموقع الألعاب\n"
            "• !all play - نقل الجميع للألعاب\n"
            "• !tip all [الكمية] - توزيع ذهب"
        ]

        # قائمة رسائل الترحيب الخاصة بالمشرفين (تُرسل عبر الهمس)
        self.mod_welcome_messages = [
            "🛡️ يا هلا ومرحبا بمشرفنا الغالي @{}! الغرفة زادت نور بوجودك ومهابتك. تم تفعيل صلاحياتك تلقائياً 🌟",
            "🛡️ حياك الله يا درع الغرفة @{}! وجودك يعطينا الأمان والنظام. صلاحياتك جاهزة وفي خدمتك ⚔️",
            "🛡️ نورتنا يا راعي الضبط والربط @{}! سعداء بعودتك لمهامك القيادية. صلاحياتك مفعلة يا بطل 🎖️",
            "🛡️ يا أهلاً بصاحب الكلمة المسموعة @{}! هيبة المشرف لا يُعلى عليها. تم تفعيل كامل صلاحياتك بنجاح ✨",
            "🛡️ أهلاً بعودتك يا صمام الأمان @{}! بوجودك كل شيء يمشي تمام. صلاحياتك تنتظرك يا غالي 🛡️"
        ]
        self.mod_welcome_index = 0

    async def on_start(self, session_metadata) -> None:
        """يتم استدعاء هذه الدالة عند تشغيل البوت ودخوله الغرفة"""
        try:
            # بدء مهمة معالجة الرسائل بالترتيب عند تشغيل المحرك
            asyncio.create_task(self.message_worker())

            # بدء مهمة مراقبة أوامر الويب
            asyncio.create_task(self.web_command_listener())

            target_pos = Position(17.50, 0.00, 22.00, facing='FrontRight')
            await self.highrise.walk_to(target_pos)
            await self.highrise.chat("🎉")
            print(
                f"تم الانتقال للموقع الافتراضي وتثبيت البوت فيه: {target_pos}")

            # تفعيل صلاحيات جميع المشرفين المتواجدين في الغرفة عند دخول البوت
            room_users = await self.highrise.get_room_users()
            for user, pos in room_users.content:
                if user.username.lower() in [
                        u.lower() for u in self.added_moderators
                ]:
                    try:
                        # اختيار رسالة ترحيب مميزة للمشرف
                        mod_msg = self.mod_welcome_messages[
                            self.mod_welcome_index].format(user.username)
                        self.mod_welcome_index = (
                            self.mod_welcome_index + 1) % len(
                                self.mod_welcome_messages)
                        await self.highrise.send_whisper(user.id, mod_msg)
                    except Exception:
                        pass

            # بدء حلقة الكلام العشوائي
            asyncio.create_task(self.random_chat_loop())
        except Exception as e:
            print(f"خطأ في الانتقال عند الدخول: {e}")

    async def bot_dance_loop(self):
        """دالة تجعل البوت يرقص بشكل عشوائي وواقعي مع فترات انتقالية سلسة"""
        emote_durations = {
            "emote-ghost-idle": 5.0,
            "idle-floorsleeping": 10.0,
            "idle_layingdown": 10.0,
            "emote-kissing": 3.0,
            "idle-uwu": 5.0,
            "sit-open": 10.0,
            "idle-floorsleeping2": 10.0,
            "idle-floating": 10.0,
            "emote-shy2": 4.0,
            "emote-slap": 2.0,
            "emoji-poop": 3.0,
            "sit-relaxed": 10.0,
            "emote-confused": 3.0,
            "emote-laughing2": 3.0,
            "dance-pinguin": 8.0,
            "dance-orangejustice": 8.0,
            "emote-hyped": 5.0
        }
        try:
            while True:
                emote_name = random.choice(list(self.emotes.keys()))
                emote_id = self.emotes[emote_name]
                await self.highrise.send_emote(emote_id)

                # جلب مدة الرقصة وطرح وقت بسيط جداً لضمان تداخل سلس بين الحركات
                duration = emote_durations.get(emote_id, 5.0)
                # تقليل المدة بمقدار 0.2 ثانية لجعل الانتقال يبدو أسرع وأكثر انسيابية
                await asyncio.sleep(max(0.1, duration - 0.2))
        except Exception as e:
            print(f"خطأ في حلقة رقص البوت: {e}")

    async def bot_movement_loop(self):
        """دالة تم تعديلها لإبقاء البوت ثابتاً في موقعه المختار"""
        try:
            fixed_pos = Position(17.50, 0.00, 22.00, facing='FrontRight')
            while True:
                # إذا لم يكن البوت يتبع أحداً، نؤكد بقاءه في الموقع المختار
                if not self.following_user_id:
                    await self.highrise.walk_to(fixed_pos)
                await asyncio.sleep(10.0)
        except Exception as e:
            print(f"خطأ في حلقة ثبات البوت: {e}")

    async def web_command_listener(self):
        """مهمة لمراقبة قاعدة بيانات الأوامر وتنفيذها في الغرفة"""
        while True:
            try:
                with SqliteDict('./web_commands.sqlite',
                                autocommit=True) as db:
                    queue = db.get('queue', [])
                    if queue:
                        for msg in queue:
                            await self.highrise.chat(msg)
                            print(f"📡 [WEB CMD] Sent: {msg}")
                        db['queue'] = []  # تفريغ الطابور بعد التنفيذ
            except Exception as e:
                print(f"Error in web_command_listener: {e}")
            await asyncio.sleep(1)

    async def run_emote_loop(self, user_id: str, emote_id: str):
        """دالة لتكرار الرقصات العامة، مع توقيتات واقعية لكل رقصة"""
        # تعريف مدد الرقصات لجعلها تبدو طبيعية وانسيابية
        emote_durations = {
            "emote-ghost-idle": 5.0,
            "idle-floorsleeping": 10.0,
            "idle_layingdown": 10.0,
            "emote-kissing": 4.0,
            "idle-uwu": 5.0,
            "sit-open": 10.0,
            "idle-floorsleeping2": 10.0,
            "idle-floating": 10.0,
            "emote-shy2": 4.0,
            "emote-slap": 2.0,
            "emoji-poop": 3.0,
            "sit-relaxed": 10.0,
            "emote-confused": 3.0,
            "emote-laughing2": 3.0,
            "dance-pinguin": 8.0,
            "dance-orangejustice": 8.0,
            "emote-hyped": 5.0
        }
        try:
            # التحقق إذا كانت الرقصة هي رقم 4 لضمان ثبات طلب المستخدم السابق (4 ثواني)
            is_emote_4 = (emote_id == self.emotes.get("4"))

            while True:
                await self.highrise.send_emote(emote_id, user_id)

                if is_emote_4:
                    wait_time = 4.0
                else:
                    # جلب مدة الرقصة وخصم جزء بسيط للسلاسة
                    duration = emote_durations.get(emote_id, 5.0)
                    wait_time = max(0.1, duration - 0.2)

                await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"خطأ في تكرار الرقصة للمستخدم: {e}")

    async def sm_reminder_loop(self):
        """حلقة لإرسال رسالة تذكيرية كل 15 ثانية عند تفعيل أمر !sm"""
        try:
            while True:
                await self.highrise.chat(
                    "🎮 للراغبين في الاستمتاع واللعب معنا، فقط اكتب كلمة (بلعب) للدخول فوراً! 🚀"
                )
                await asyncio.sleep(15.0)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"خطأ في حلقة التذكير: {e}")

    async def is_admin(self, user_id: str) -> bool:
        """التحقق مما إذا كان المستخدم مشرفاً في الغرفة أو صاحب البوت"""
        # التحقق من قائمة أصحاب البوت (الأسماء)
        room_users = await self.highrise.get_room_users()
        user_obj = next(
            (u for u, pos in room_users.content if u.id == user_id), None)

        if user_obj:
            if user_obj.username in self.bot_owners or user_obj.username.lower(
            ) in [u.lower() for u in self.added_moderators]:
                return True
        return False

    # تم حذف التكرار لضمان عمل الأوامر بشكل سليم

    async def start_game_countdown(self):
        """عداد تنازلي لبدء اللعبة"""
        await asyncio.sleep(10)  # انتظر 10 ثواني لتجميع المشاركين
        if len(self.game_participants) < 1:
            await self.highrise.chat("❌ تم إلغاء اللعبة لعدم وجود مشاركين.")
            self.game_active = False
            return

        for i in range(5, 0, -1):
            await self.highrise.chat(f"⏱️ ستبدأ الجولة الأولى خلال {i}...")
            await asyncio.sleep(1)

        self.game_started = True  # قفل الانضمام
        await self.start_new_round()

    async def start_new_round(self):
        """بدء جولة جديدة بسؤال عشوائي"""
        self.game_letter = random.choice("أبتثجحخدذرزسشصضطظعغفقكلمنهوي")
        self.game_category = random.choice(self.categories)
        await self.highrise.chat(
            f"📍 الجولة 【 {self.game_round} / {self.max_rounds} 】\nأعطني اسم 【 {self.game_category} 】 يبدأ بحرف 【 {self.game_letter} 】"
        )
        self.game_awaiting_answers = True

    async def random_chat_loop(self):
        """حلقة لإرسال رسائل عشوائية في الدردشة كل فترة"""
        while True:
            try:
                # انتظار فترة عشوائية بين 5 إلى 10 دقائق
                await asyncio.sleep(random.randint(300, 600))

                # التحقق إذا كانت الغرفة فيها أشخاص غير البوت
                room_users = await self.highrise.get_room_users()
                if len(room_users.content) > 1:
                    phrase = random.choice(self.random_phrases)
                    await self.highrise.chat(phrase)
            except Exception as e:
                print(f"خطأ في حلقة الكلام العشوائي: {e}")
                await asyncio.sleep(60)

    async def on_user_join(self, user: User,
                           position: Position | AnchorPosition) -> None:
        """يتم استدعاء هذه الدالة عندما ينضم لاعب جديد للغرفة"""
        try:
            # تسجيل دخول المستخدمين
            print(f"📥 [JOIN] @{user.username} joined the room.")

            # التحقق من أن المستخدم مشرف في قاعدة البيانات
            is_mod = user.username.lower() in [
                u.lower() for u in self.added_moderators
            ]

            # إعادة المسجون تلقائياً عند دخوله
            if user.id in self.muted_users:
                jail_pos = Position(17.00, 5.75, 18.00, facing='FrontRight')
                await self.highrise.teleport(user.id, jail_pos)
                await self.highrise.chat(f"🔒 @{user.username}، عد لسجنك! لا يسمح لك بالخروج.")
                return

            # اختيار رسالة الترحيب بالترتيب
            welcome_msg = self.welcome_messages[self.welcome_index]
            self.welcome_index = (self.welcome_index + 1) % len(
                self.welcome_messages)

            if is_mod:
                # ترحيب خاص ومميز للمشرف عند دخوله (عبر الهمس فقط)
                try:
                    mod_msg = random.choice(self.mod_welcome_messages).format(
                        user.username)
                    await self.highrise.send_whisper(user.id, mod_msg)
                except:
                    pass
                return
            else:
                await self.highrise.chat(
                    welcome_msg.replace("{}", f"@{user.username}"))

            # إرسال 20 قلباً لكل شخص ينضم للغرفة
            for _ in range(20):
                await self.highrise.react("heart", user.id)
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"خطأ في إرسال رسالة الترحيب: {e}")

    async def on_user_move(self, user: User,
                           destination: Position | AnchorPosition) -> None:
        """يتم استدعاء هذه الدالة عندما يتحرك لاعب"""
        try:
            # التحقق إذا كان المستخدم مثبت (frozen)
            if user.id in self.frozen_users:
                frozen_pos = self.frozen_users[user.id]
                if isinstance(destination, Position) and isinstance(frozen_pos, Position):
                    # حساب المسافة (بشكل بسيط) أو فقط إعادته إذا تحرك
                    if destination.x != frozen_pos.x or destination.z != frozen_pos.z:
                        await self.highrise.teleport(user.id, frozen_pos)
                return

            # إذا كان البوت يتبع هذا المستخدم
            if self.following_user_id == user.id:
                if isinstance(destination, Position):
                    # البوت يتحرك خلف المستخدم بقليل
                    target_pos = Position(destination.x, destination.y,
                                          destination.z, destination.facing)
                    await self.highrise.walk_to(target_pos)

            # ضمان عودة البوت لموقعه إذا لم يكن يتبع أحداً
            elif not self.following_user_id:
                fixed_pos = Position(17.50, 0.00, 22.00, facing='FrontRight')
                # نستخدم مسافة بسيطة كحد للتحقق لضمان الثبات
                pass
        except Exception as e:
            print(f"خطأ في معالجة الحركة: {e}")

    async def on_whisper(self, user: User, message: str) -> None:
        """يتم استدعاء هذه الدالة عندما يهمس لاعب للبوت"""
        try:
            # تسجيل الهمس (Log)
            print(f"🤫 [WHISPER] @{user.username}: {message}")

            # التحقق إذا كان الشخص الذي يهمس مشرفاً أو صاحب البوت
            if await self.is_admin(user.id):
                # جعل البوت يرسل الرسالة في الدردشة العامة
                await self.highrise.chat(message)
            else:
                # إذا لم يكن مشرفاً، يمكن للبوت الرد عليه بشكل خاص أو تجاهله
                # هنا سنكتفي بعدم إرسال الرسالة للدردشة العامة
                pass
        except Exception as e:
            print(f"خطأ في معالجة الهمس: {e}")

    async def message_worker(self):
        """عامل لمعالجة الرسائل من الطابور واحدة تلو الأخرى لضمان الترتيب"""
        while True:
            user, message = await self.message_queue.get()
            try:
                await self.process_chat(user, message)
            except Exception as e:
                print(f"خطأ في معالجة رسالة من الطابور: {e}")
            finally:
                self.message_queue.task_done()

    async def on_chat(self, user: User, message: str) -> None:
        """يتم استدعاء هذه الدالة عندما يرسل لاعب رسالة في الدردشة"""
        # إضافة الرسالة إلى الطابور لضمان المعالجة بالترتيب
        await self.message_queue.put((user, message))

    async def process_chat(self, user: User, message: str) -> None:
        """المعالجة الفعلية للرسالة"""
        try:
            # منع المسجون أو الموجود في الزبالة من استخدام أي أوامر
            if user.id in self.muted_users or user.id in self.frozen_users:
                # إذا كانت الرسالة تبدأ بـ ! أو هي أمر معروف
                # نسمح بالرقص فقط (الذي يكون عبارة عن رقم أو اسم رقصة من الديكشنري)
                is_emote = message.strip() in self.emotes
                if not is_emote:
                    if message.startswith("!") or any(message.startswith(cmd) for cmd in ["سجن", "حرر", "كف", "loop", "زبالة"]):
                        await self.highrise.send_whisper(user.id, "❌ عذراً، لا يمكنك استخدام الأوامر في وضعك الحالي.")
                        return

            # تسجيل المحادثات في قاعدة البيانات للموقع
            import datetime
            # نفتح قاعدة البيانات في كل مرة لضمان الاستقرار وعدم فقدان البيانات
            with SqliteDict('./chat_logs.sqlite', autocommit=True) as chat_db:
                logs = chat_db.get('logs', [])
                logs.append({
                    'username':
                    user.username,
                    'message':
                    message,
                    'time':
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # الاحتفاظ بآخر 2000 رسالة لضمان استقرار أطول
                chat_db['logs'] = logs[-2000:]

            # تسجيل المحادثات (Log)
            print(f"💬 [CHAT] @{user.username}: {message}")

            message = message.strip()
            clean_message = message.lower()

            # منع استخدام الأوامر على المستخدم @_PMW (إلا لصاحب البوت _7rbi)
            if "@_pmw" in clean_message and user.username.lower() != "_7rbi":
                await self.highrise.chat(
                    f"⚠️ عذراً @{user.username}، لا يمكنك استخدام الأوامر على هذا المستخدم المحمي."
                )
                return

            # أمر انتقال البوت للموقع المحدد بنقطة
            if message == ".":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                dot_pos = Position(17.50, 6.00, 0.50, facing='BackLeft')
                await self.highrise.walk_to(dot_pos)
                return

            # أمر مسجون للسجن الجديد
            if message == "مسجون":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                if await self.is_admin(user.id): # This check is redundant but following the user's logic for "admin only"
                     # To be safe, let's just make it admin only as requested
                     pass
                
                # We need to target a user for "trash" logic, but the user asked to change jail تثبيت to trash.
                # If "مسجون" is a self-jail command, we'll keep it admin only.
                jail_pos_new = Position(14.50, 0.00, 23.00, facing='BackRight')
                await self.highrise.teleport(user.id, jail_pos_new)
                # self.frozen_users[user.id] = jail_pos_new  # Removed freezing from jail
                await self.highrise.chat(
                    f"🔒 تم سجن @{user.username} في مكانه الجديد.")
                return

            # أمر تصفير المشرفين
            if clean_message == "!r":
                room_users = await self.highrise.get_room_users()
                user_obj = next(
                    (u for u, pos in room_users.content if u.id == user.id),
                    None)
                if not user_obj or user_obj.username not in self.bot_owners:
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر لصاحب البوت فقط."
                    )
                    return

                if not self.added_moderators:
                    await self.highrise.chat(
                        "⚠️ لا يوجد مشرفون مضافون حالياً لتصفير القائمة.")
                    return

                self.added_moderators = set()
                self.db['mods'] = []
                await self.highrise.chat("✅ تم تصفير قائمة مشرفي البوت بنجاح!")
                return

            # أمر إضافة مشرف "!add admin @username"
            elif message.startswith("!add admin @"):
                room_users = await self.highrise.get_room_users()
                user_obj = next(
                    (u for u, pos in room_users.content if u.id == user.id),
                    None)
                if not user_obj or user_obj.username not in self.bot_owners:
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر لصاحب البوت فقط."
                    )
                    return

                target_username = message.split("@")[1].strip()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    # تحديث القائمة المحلية من قاعدة البيانات للتأكد من المزامنة بعد إعادة التشغيل
                    self.added_moderators = set(self.db.get('mods', []))

                    # التحقق من أن الاسم ليس مضافاً بالفعل (مع تجاهل حالة الأحرف)
                    if target_user.username.lower() in [
                            u.lower() for u in self.added_moderators
                    ]:
                        await self.highrise.chat(
                            f"⚠️ تنبيه: @{target_username} مضاف بالفعل كمشرف في البوت."
                        )
                        return

                    # إضافة للقائمة الحالية وقاعدة البيانات
                    self.added_moderators.add(target_user.username)
                    self.db['mods'] = list(self.added_moderators)

                    await self.highrise.chat(
                        f"✅ تم تعيين @{target_username} كمشرف في البوت بنجاح!")
                else:
                    await self.highrise.chat(
                        f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر إزالة مشرف "!unadmin @username"
            elif message.startswith("!unadmin @"):
                room_users = await self.highrise.get_room_users()
                user_obj = next(
                    (u for u, pos in room_users.content if u.id == user.id),
                    None)
                if not user_obj or user_obj.username not in self.bot_owners:
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر لصاحب البوت فقط."
                    )
                    return

                target_username = message.split("@")[1].strip()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    if target_user.username.lower() in [
                            u.lower() for u in self.added_moderators
                    ]:
                        username_to_remove = next(
                            u for u in self.added_moderators
                            if u.lower() == target_user.username.lower())
                        self.added_moderators.remove(username_to_remove)
                        # تحديث قاعدة البيانات
                        self.db['mods'] = list(self.added_moderators)

                        await self.highrise.chat(
                            f"✅ تم إزالة @{target_username} من قائمة مشرفي البوت."
                        )
                    else:
                        await self.highrise.chat(
                            f"⚠️ @{target_username} ليس مشرفاً في البوت أصلاً."
                        )
                else:
                    await self.highrise.chat(
                        f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر قائمة الأوامر العامة
            elif clean_message == "!commands" or clean_message == "اوامر":
                # الأوامر العامة للجميع
                help_text = "📜 قائمة الأوامر العامة:\n"
                help_text += "🕺 الرقص: (1-17) أو اسم الرقصة\n"
                help_text += "🔄 رقص لانهائي: loop (رقم/اسم) | إيقاف: 0\n"
                help_text += "💖 قلوب: h @الاسم [العدد] (إرسال قلوب)\n"
                help_text += "💋 قبلة: مح @الاسم (البوت يقبلك)\n"
                help_text += "🤖 ذكاء اصطناعي: نادني بـ (عبندي، عبند، عبنود)\n"
                help_text += "🛡️ مساعدة: اوامر"

                await self.highrise.chat(help_text)
                return

            # أمر المساعدة !help
            elif clean_message == "!help":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                for part in self.admin_commands:
                    await self.highrise.send_whisper(user.id, part)
                    await asyncio.sleep(0.5)  # تأخير بسيط لتجنب سبام الرسائل
                return

            # أمر !go لنقل البوت لموقعه الافتراضي وإيقاف التذكير وإلغاء أمر بلعب
            elif clean_message == "!go":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return

                # إيقاف التذكير عند العودة للموقع الافتراضي
                if self.sm_reminder_task:
                    self.sm_reminder_task.cancel()
                    self.sm_reminder_task = None

                # إلغاء أمر بلعب للجميع
                self.play_command_enabled = False

                target_pos = Position(17.50, 0.00, 21.50, facing='FrontRight')
                await self.highrise.walk_to(target_pos)
                await self.highrise.chat(
                    "🚫 تم إيقاف نظام اللعب والعودة للموقع الافتراضي! 🏃‍♂️")
                return

            # أمر !play أو لعب لنقل المستخدم لموقع محدد
            elif clean_message in ["!play", "لعب"]:
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_pos = Position(11.00, 0.00, 11.00, facing='FrontRight')
                await self.highrise.teleport(user.id, target_pos)
                return

            # أمر بلعب لنقل المستخدم لموقع محدد (مستقل)
            elif clean_message == "بلعب":
                if not self.play_command_enabled and not await self.is_admin(
                        user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، أمر بلعب غير مفعل حالياً. يجب تفعيله عبر !give أو !sm أولاً."
                    )
                    return
                target_pos = Position(5.00, 0.00, 10.00, facing='FrontRight')
                await self.highrise.teleport(user.id, target_pos)
                return

            # أمر !give لتفعيل أمر بلعب (للمشرفين فقط، بدون نقل)
            elif clean_message == "!give":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط لتفعيل نظام اللعب."
                    )
                    return

                self.play_command_enabled = True
                await self.highrise.chat(
                    "✅ تم تفعيل أمر 'بلعب' لجميع من في الغرفة!")
                return

            # أمر !all play لنقل جميع من في الغرفة لموقع محدد
            elif clean_message == "!all play" or clean_message == "لعب الكل":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return

                target_pos = Position(10.50, 0.00, 9.50, facing='FrontRight')
                room_users = await self.highrise.get_room_users()
                bot_user = await self.highrise.get_self_user()

                await self.highrise.chat("📢 يتم نقل الجميع إلى منطقة اللعب...")
                for u, pos in room_users.content:
                    # لا ننقل البوت
                    if u.id != bot_user.user_id:
                        try:
                            await self.highrise.teleport(u.id, target_pos)
                        except Exception as e:
                            print(f"فشل نقل {u.username}: {e}")
                return

            # أمر out لنقل شخص محدد لموقع محدد
            elif clean_message.startswith("out @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)
                if target_user:
                    # نقل الشخص للموقع الجديد المحدد من قبل المستخدم
                    await self.highrise.teleport(
                        target_user.id,
                        Position(9.50, 0.00, 14.00, facing='FrontRight'))
                    await self.highrise.chat(
                        f"🚪 تم إرسال @{target_username} للخارج.")
                else:
                    await self.highrise.chat(
                        f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر النقل للموقع المحدد (نزلني)
            elif clean_message == "نزلني":
                target_pos = Position(9.00, 0.75, 23.00, facing='FrontRight')
                await self.highrise.teleport(user.id, target_pos)
                return

            # أمر !d لنقل شخص محدد لموقع محدد
            elif clean_message.startswith("!d @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    target_pos = Position(9.00,
                                          0.75,
                                          23.00,
                                          facing='FrontRight')
                    await self.highrise.teleport(target_user.id, target_pos)
                else:
                    await self.highrise.chat(
                        f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر النقطة للانتقال لموقع محدد وبدء التذكير
            elif clean_message == "!sm":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return

                # تفعيل أمر "دخلني" تلقائياً عند كتابة !sm
                self.play_command_enabled = True

                # إلغاء أي مهمة تذكير سابقة إذا وجدت
                if self.sm_reminder_task:
                    self.sm_reminder_task.cancel()

                target_pos = Position(5.50, 0.00, 18.50, facing='FrontRight')
                await self.highrise.walk_to(target_pos)

                # بدء مهمة التذكير كل 7 ثوانٍ
                self.sm_reminder_task = asyncio.create_task(
                    self.sm_reminder_loop())
                return

            # أمر !admins لإظهار جميع المشرفين
            elif clean_message == "!admins":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                # عرض قائمة المشرفين
                if not self.added_moderators:
                    await self.highrise.chat("📜 لا يوجد مشرفون مضافون حالياً.")
                else:
                    mods_list = "📜 قائمة المشرفين المضافين:\n"
                    mods_list += "\n".join(
                        [f"• @{m}" for m in self.added_moderators])
                    await self.highrise.chat(mods_list)
                return

            # أمر "تف" وامنشن شخص
            elif message.startswith("تف @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    # جلب موقع الشخص المستهدف حالياً
                    target_pos = next((pos for u, pos in room_users.content
                                       if u.id == target_user.id), None)

                    if target_pos:
                        # حفظ الموقع الحالي للعودة إليه
                        current_bot_pos = Position(17.50,
                                                   0.00,
                                                   21.50,
                                                   facing='FrontRight')

                        # الذهاب لموقع الشخص
                        await self.highrise.walk_to(
                            Position(target_pos.x,
                                     target_pos.y,
                                     target_pos.z,
                                     facing='FrontRight'))

                        # انتظار بسيط للوصول (تقريبي) ثم إرسال الرسالة
                        await asyncio.sleep(3)
                        await self.highrise.chat(
                            f"ختفووووووو 💦 @{target_username}")

                        # العودة للمكان الأصلي
                        await asyncio.sleep(1)
                        await self.highrise.walk_to(current_bot_pos)
                    else:
                        await self.highrise.chat(
                            f"❓ لم أستطع تحديد موقع @{target_username}!")
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username}!")
                return

            # أمر إرسال قلوب "h @username [عدد]"
            elif message.startswith("h @"):
                parts = message.split()
                if len(parts) < 2:
                    return

                target_username = parts[1].replace("@", "").strip()

                # تحديد العدد (افتراضي 20)
                count = 20
                if len(parts) >= 3 and parts[2].isdigit():
                    count = int(parts[2])
                    # وضع حد أقصى للقلوب لمنع التعليق
                    if count > 100:
                        count = 100

                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    await self.highrise.chat(
                        f"💖 جاري إرسال {count} قلباً إلى @{target_username}")
                    for _ in range(count):
                        await self.highrise.react("heart", target_user.id)
                        await asyncio.sleep(0.1)
                else:
                    await self.highrise.chat(
                        f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر "مح" وامنشن شخص
            elif message.startswith("مح @"):
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    target_pos = next((pos for u, pos in room_users.content
                                       if u.id == target_user.id), None)
                    if target_pos:
                        current_bot_pos = Position(5.50,
                                                   0.00,
                                                   18.50,
                                                   facing='FrontRight')
                        await self.highrise.walk_to(
                            Position(target_pos.x,
                                     target_pos.y,
                                     target_pos.z,
                                     facing='FrontRight'))
                        await asyncio.sleep(3)
                        await self.highrise.chat(f"مححححح 💋 @{target_username}"
                                                 )
                        await asyncio.sleep(1)
                        await self.highrise.walk_to(current_bot_pos)
                    else:
                        await self.highrise.chat(
                            f"❓ لم أستطع تحديد موقع @{target_username}!")
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username}!")
                return

            # أمر "اتبع" وامنشن شخص
            elif message.startswith("اتبع @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    if await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنني اتباع مشرف!")
                        return
                    await self.highrise.chat(
                        f"🚶‍♂️ أبشر، بدأت أتبعك يا @{target_username}!")
                    self.following_user_id = target_user.id
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username}!")
                return

            # أمر التوقف عن اللحاق
            elif clean_message == "!stop":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                if self.following_user_id:
                    self.following_user_id = None
                    await self.highrise.chat("✅ تم إيقاف اللحاق بنجاح.")
                else:
                    await self.highrise.chat("⚠️ أنا لا أتبع أحداً حالياً.")
                return

            # أمر قائمة المشرفين
            elif clean_message == "!admins":
                # تحديث القائمة من قاعدة البيانات لضمان دقة البيانات
                current_mods = list(self.added_moderators)
                if not current_mods:
                    await self.highrise.chat(
                        "📜 لا يوجد مشرفون مضافون حالياً في البوت.")
                else:
                    mods_list = "📜 قائمة مشرفي البوت:\n" + "\n".join(
                        [f"• @{mod}" for mod in current_mods])
                    await self.highrise.chat(mods_list)
                return

            # التفاعل مع الذكاء الاصطناعي عند ذكر الاسم في أي مكان بالجملة
            elif any(name in clean_message
                     for name in ["عبنود", "عبنودي", "عبنيد"]):
                # استخراج السؤال (الجملة كاملة)
                question = message.strip()

                try:
                    # جلب معلومات الغرفة لزيادة الذكاء
                    room_users = await self.highrise.get_room_users()
                    user_count = len(room_users.content)
                    
                    # التحقق من صلاحيات السائل
                    is_admin_user = await self.is_admin(user.id)
                    
                    system_prompt = (
                        f"أنت '{self.ai_name}'، بوت ذكي جداً في Highrise. "
                        f"صاحب الغرفة هو '_7rbi'. "
                        f"السائل {'مشرف' if is_admin_user else 'لاعب عادي'}. "
                        "كن سريعاً جداً، رد بذكاء وسلاسة سعودية بيضاء. "
                        "ردودك يجب أن تكون قصيرة جداً (سطر واحد) وتفاعلية.")

                    # إرسال الطلب لـ OpenAI مع إعدادات للسرعة
                    response = openai_legacy.ChatCompletion.create(
                        model="gpt-4o-mini",  # استخدام موديل أسرع
                        messages=[{
                            "role": "system",
                            "content": system_prompt
                        }, {
                            "role": "user",
                            "content": f"من @{user.username}: {question}"
                        }],
                        max_tokens=50,  # تقليل التوكنز لسرعة الاستجابة
                        temperature=0.7,
                        presence_penalty=0.5)
                    ai_response = response.choices[0].message.content.strip()
                    await self.highrise.chat(ai_response)
                except Exception as e:
                    print(f"AI Error: {e}")
                    await self.highrise.chat(f"هلا @{user.username}، سم؟")
                return

            # أمر الطرد !kick @username
            elif clean_message.startswith("!kick @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)
                if target_user:
                    try:
                        await self.highrise.moderate_room(
                            target_user.id, "kick")
                        await self.highrise.chat(
                            f"✅ تم طرد @{target_username} بنجاح!")
                    except Exception as e:
                        await self.highrise.chat(
                            f"❌ فشل طرد @{target_username}.")
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username}!")
                return

            # أمر !ban لحظر المستخدم من الغرفة
            elif clean_message.startswith("!ban @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)
                if target_user:
                    # حماية المشرفين
                    if await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك حظر مشرف آخر!")
                        return
                    try:
                        await self.highrise.moderate_room(
                            target_user.id, "ban",
                            24)  # حظر لمدة 24 ساعة افتراضياً
                        await self.highrise.chat(
                            f"🚫 تم حظر @{target_username} من الغرفة!")
                    except Exception as e:
                        await self.highrise.chat(
                            f"❌ فشل حظر @{target_username}.")
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username}!")
                return

            # تصحيح الأوامر الخاطئة
            if "ثبت" in message and not message.startswith("ثبت @"):
                # تم إزالة تصحيح هذا الأمر بناءً على طلب المستخدم
                pass
            elif "فك" in message and not message.startswith("فك @"):
                # تم إزالة تصحيح هذا الأمر بناءً على طلب المستخدم
                pass
            elif "هات" in message and not message.startswith("هات @"):
                # تم إزالة تصحيح هذا الأمر بناءً على طلب المستخدم
                pass
            elif "مرجح" in message and not message.startswith("مرجح @"):
                # تم إزالة تصحيح هذا الأمر بناءً على طلب المستخدم
                pass
            elif "توقيف" in message and not message.startswith("توقيف @"):
                await self.highrise.chat("💡 الطريقة الصحيحة: توقيف @الاسم")
                return
            elif "فراغ" in message and not message.startswith("فراغ @"):
                await self.highrise.chat("💡 الطريقة الصحيحة: فراغ @الاسم")
                return
            elif "كتم" in message and not message.startswith("كتم @"):
                # تم إزالة تصحيح هذا الأمر بناءً على طلب المستخدم
                pass

            # أمر !tip لتوزيع الذهب
            elif clean_message.startswith("!tip"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                try:
                    parts = clean_message.split()
                    # إذا كتب !tip فقط أو !tip all بدون رقم
                    if len(parts) < 3 or (len(parts) >= 2
                                          and parts[1] != "all"):
                        await self.highrise.chat(
                            "💡 طريقة استخدام أمر توزيع الذهب:\n!tip all [الكمية]\nمثال: !tip all 1"
                        )
                        return

                    amount_str = parts[2]
                    if not amount_str.isdigit():
                        await self.highrise.chat(
                            "⚠️ يرجى إدخال كمية صحيحة (رقم).")
                        return

                    amount = int(amount_str)
                    room_users = await self.highrise.get_room_users()
                    # استخدام get_self_user() بدلاً من me()
                    bot_user_data = await self.highrise.get_self_user()
                    bot_user_id = bot_user_data.user_id

                    eligible_users = [
                        u for u, pos in room_users.content
                        if u.id != bot_user_id
                    ]

                    if not eligible_users:
                        await self.highrise.chat(
                            "⚠️ لا يوجد أحد في الغرفة لإعطائه الذهب.")
                        return

                    await self.highrise.chat(
                        f"💰 جاري توزيع {amount} ذهبة على {len(eligible_users)} شخص..."
                    )

                    for target_user in eligible_users:
                        try:
                            await self.highrise.tip_user(
                                target_user.id, amount)
                            await asyncio.sleep(0.5)  # تأخير كافٍ لتجنب الحظر
                        except Exception as e:
                            print(
                                f"فشل إعطاء الذهب لـ {target_user.username}: {e}"
                            )

                    await self.highrise.chat(
                        "✅ تم توزيع الذهب على الجميع بنجاح!")
                except Exception as e:
                    print(f"خطأ في أمر توزيع الذهب: {e}")
                return
            # تنفيذ الرقصات
            if clean_message in self.emotes:
                # إيقاف أي رقصة لانهائية سابقة للمستخدم
                if user.id in self.emote_loop_tasks:
                    self.emote_loop_tasks[user.id].cancel()
                    del self.emote_loop_tasks[user.id]

                # إرسال الرقصة للمستخدم فقط
                emote_id = self.emotes[clean_message]
                await self.highrise.send_emote(emote_id, user.id)
                return

            # أمر الحظر "!ban @username"
            elif message.startswith("!ban @"):
                if user.username not in self.bot_owners:
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر لصاحب البوت فقط."
                    )
                    return
                await self.handle_ban(user, message)
                return

            # منع المسجون من قول "نزلني"
            elif clean_message == "نزلني":
                if user.id in self.muted_users:
                    await self.highrise.send_whisper(user.id, "❌ لا يمكنك استخدام هذا الأمر وأنت مسجون.")
                    return
                # السلوك الافتراضي لمن ليس مسجوناً
                ground_pos = Position(17.50, 0.00, 26.00, facing='FrontRight')
                await self.highrise.teleport(user.id, ground_pos)
                await self.highrise.chat(
                    f"✅ تم إنزالك للدور الأرضي يا @{user.username}")
                return

            # أمر السجن
            # أمر السجن
            elif message.startswith("سجن @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return

                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next((u for u, pos in room_users.content if u.username.lower() == target_username.lower()), None)

                if target_user:
                    # منع سجن المشرفين الآخرين أو صاحب البوت
                    if await self.is_admin(target_user.id):
                         await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك سجن مشرف آخر!")
                         return

                    # منع المشرف من سجن نفسه
                    if target_user.id == user.id:
                        await self.highrise.chat(
                            f"❌ عذراً @{user.username}، لا يمكنك سجن نفسك!")
                        return

                    jail_pos = Position(17.00, 5.75, 18.00, facing='FrontRight')
                    await self.highrise.teleport(target_user.id, jail_pos)
                    try:
                        await self.highrise.moderate_room(target_user.id, "mute", 3153600000)
                        self.muted_users.add(target_user.id)
                    except Exception as e:
                        print(f"خطأ في عمل ميوت تلقائي: {e}")
                    await self.highrise.chat(f"🔒 تم سجن @{target_username} وعمل ميوت لمدة 100 سنة!")
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر الزبالة
            elif message.startswith("زبالة @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next((u for u, pos in room_users.content if u.username.lower() == target_username.lower()), None)

                if target_user:
                    if await self.is_admin(target_user.id):
                         await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك فعل ذلك بمشرف!")
                         return

                    trash_pos = Position(16.50, 0.00, 26.50, facing='FrontRight')
                    self.frozen_users[target_user.id] = trash_pos
                    await self.highrise.teleport(target_user.id, trash_pos)
                    await self.highrise.chat(f"🚮 تم وضع @{target_username} في الزبالة وتثبيته! لن تستطيع التحرك حتى يرحمك @{user.username}")
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر رحمتك لفك تثبيت أمر زبالة فقط
            elif message.startswith("رحمتك @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next((u for u, pos in room_users.content if u.username.lower() == target_username.lower()), None)

                if target_user:
                    if target_user.id in self.frozen_users:
                        frozen_pos = self.frozen_users[target_user.id]
                        # نعتبره في الزبالة إذا كان في موقع الزبالة (16.50, 0.00, 26.50)
                        if isinstance(frozen_pos, Position) and frozen_pos.x == 16.50 and frozen_pos.z == 26.50:
                            del self.frozen_users[target_user.id]
                            await self.highrise.chat(f"✨ تم العفو عن @{target_username} من الزبالة، يمكنك التحرك الآن!")
                        else:
                            await self.highrise.chat(f"⚠️ @{target_username} ليس في الزبالة، استخدم (فك @{target_username}) لإلغاء تثبيته.")
                    else:
                        await self.highrise.chat(f"⚠️ @{target_username} ليس مثبتاً.")
                else:
                    await self.highrise.chat(f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر التحرير
            elif message.startswith("حرر @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return

                target_username = message.split("@")[1].strip()

                # منع المشرف المسجون من تحرير نفسه
                if target_username.lower() == user.username.lower():
                    await self.highrise.chat(
                        f"❌ عذراً @{user.username}، لا يمكنك تحرير نفسك!")
                    return

                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    # التحقق مما إذا كان المستخدم مسجوناً بالفعل (لديه ميوت طويل الأمد)
                    # ملاحظة: بما أننا أزلنا التجميد، نعتمد على التحقق من الميوت أو موقع السجن

                    # للحفاظ على المنطق، سنفترض أن المستخدم مسجون إذا كان موقعه قريباً من السجن 
                    # أو ببساطة نقوم بالتحرير دائماً إذا كان موجوداً، ولكن لإظهار رسالة "ليس مسجوناً"
                    # سنقوم بتخزين حالة السجن في سيت (set) خاص

                    if target_user.id in self.muted_users:
                        # إزالة الميوت تلقائياً (عبر عمل ميوت لمدة ثانية واحدة لإلغاء الميوت السابق)
                        try:
                            await self.highrise.moderate_room(
                                target_user.id, "mute", 1)
                            self.muted_users.discard(target_user.id)
                        except Exception as e:
                            print(f"خطأ في إزالة الميوت تلقائياً: {e}")

                        # إعادة المستخدم إلى الموقع الأساسي
                        down_pos = Position(17.50,
                                            0.00,
                                            22.00,
                                            facing='FrontRight')
                        await self.highrise.teleport(target_user.id, down_pos)

                        # إزالة من قائمة المجمدين إذا كان موجوداً
                        if target_user.id in self.frozen_users:
                            del self.frozen_users[target_user.id]

                        await self.highrise.chat(
                            f"🔓 تم تحرير @{target_username} وإعادته للموقع الأساسي وإزالة الميوت عنه بنجاح!"
                        )
                    else:
                        await self.highrise.chat(
                            f"⚠️ @{target_username} ليس مسجوناً.")
                else:
                    await self.highrise.chat(
                        f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر كف
            elif message.startswith("كف @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    await self.highrise.send_emote("emote-judochop", user.id)
                    await self.highrise.send_emote("emote-fainting",
                                                   target_user.id)
                else:
                    await self.highrise.chat(
                        f"❓ لم أجد @{target_username} في الغرفة.")
                return

            # أمر الكتم "!mute @username"
            elif message.startswith("!mute @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                parts = message.split()
                if len(parts) >= 2:
                    target_username = parts[1].strip("@")
                    
                    # التحقق إذا كان الهدف مشرفاً
                    room_users = await self.highrise.get_room_users()
                    target_user = next((u for u, p in room_users.content if u.username.lower() == target_username.lower()), None)
                    
                    if target_user and await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك كتم مشرف آخر!")
                        return

                    duration = 3600
                    if len(parts) > 2:
                        try:
                            time_str = parts[2].lower()
                            if time_str.endswith('m'): duration = int(time_str[:-1]) * 60
                            elif time_str.endswith('h'): duration = int(time_str[:-1]) * 3600
                            elif time_str.endswith('d'): duration = int(time_str[:-1]) * 86400
                            else: duration = int(time_str)
                        except: pass
                    
                    if target_user:
                        try:
                            await self.highrise.moderate_room(target_user.id, "mute", duration)
                            self.muted_users.add(target_user.id)
                            await self.highrise.chat(f"🔇 تم كتم @{target_username} بنجاح.")
                        except Exception as e:
                            await self.highrise.chat(f"❌ فشل كتم @{target_username}.")
                    else:
                        await self.highrise.chat(f"❓ لم أجد @{target_username}!")
                return

            # أمر إلغاء الكتم "!unmute @username" أو "!unban @username"
            elif message.startswith("!unmute @") or message.startswith(
                    "!unban @"):
                await self.handle_unmute(user, message)
                return

            # أمر إيقاف الرقصة (0) أو stop loop
            elif clean_message == "0" or clean_message == "stop loop":
                if user.id in self.emote_loop_tasks:
                    self.emote_loop_tasks[user.id].cancel()
                    del self.emote_loop_tasks[user.id]
                    await self.highrise.chat(
                        f"⏹️ تم إيقاف الرقصة اللانهائية لـ {user.username}.")
                else:
                    await self.highrise.chat(
                        "💡 ليس لديك رقصة لانهائية لتعطيلها.")
                return

            # أمر الرقصة اللانهائية: loop رقم الرقصة أو اسمها
            if clean_message.startswith("loop "):
                emote_key = clean_message.replace("loop ", "").strip()
                if emote_key in self.emotes:
                    # إيقاف أي رقصة لانهائية سابقة
                    if user.id in self.emote_loop_tasks:
                        self.emote_loop_tasks[user.id].cancel()

                    emote_id = self.emotes[emote_key]
                    task = asyncio.create_task(
                        self.run_emote_loop(user.id, emote_id))
                    self.emote_loop_tasks[user.id] = task
                    await self.highrise.chat(
                        f"🚀 بدأت الرقصة اللانهائية لـ {user.username} (الرقصة: {emote_key})!"
                    )
                else:
                    await self.highrise.chat(
                        f"⚠️ الرقصة '{emote_key}' غير موجودة.")
                return

            # أمر !come لاتباع المستخدم
            if message.lower() == "!come":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                self.following_user_id = user.id
                await self.highrise.chat(
                    f"سأتبعك الآن يا {user.username}! 🏃‍♂️")

            # أمر !stop للتوقف عن الاتباع
            elif message.lower() == "!stop":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                if self.following_user_id:
                    self.following_user_id = None
                    await self.highrise.chat("توقفت عن الاتباع. 👋")
                else:
                    await self.highrise.chat("أنا لا أتبع أحداً حالياً.")
                return

            # أمر اتبع @username لاتباع شخص محدد
            elif message.startswith("اتبع @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)

                if target_user:
                    if await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنني اتباع مشرف!")
                        return
                    self.following_user_id = target_user.id
                    await self.highrise.chat(
                        f"سأتبع @{target_user.username} الآن! 🏃‍♂️")
                else:
                    await self.highrise.chat(
                        f"لم أجد {target_username} in the room.")
                return

            # أمر نسخ الملابس !e @username
            elif message.startswith("!e "):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                parts = message.split()
                if len(parts) > 1:
                    target_username = parts[1].strip("@")
                    room_users = await self.highrise.get_room_users()
                    target_user = None
                    for u, _ in room_users.content:
                        if u.username.lower() == target_username.lower():
                            target_user = u
                            break
                    if target_user:
                        outfit_response = await self.highrise.get_user_outfit(
                            target_user.id)
                        await self.highrise.set_outfit(outfit_response.outfit)
                        await self.highrise.chat(
                            f"تم نسخ ملابس {target_user.username} بنجاح! 😎")
                    else:
                        await self.highrise.chat(
                            f"لم أجد {target_username} في الغرفة.")
                return

            # أمر التثبيت !j @username
            elif message.startswith("!j @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = None
                target_pos = None
                for u, pos in room_users.content:
                    if u.username.lower() == target_username.lower():
                        target_user = u
                        target_pos = pos
                        break
                if target_user and target_pos:
                    self.frozen_users[target_user.id] = target_pos
                    await self.highrise.chat(f"🔒 تم تثبيت @{target_user.username} في مكانه بنجاح!")
                else:
                    await self.highrise.chat(f"❓ لم أجد {target_username} في الغرفة.")
                return

            # أمر فك التجميد "فك @username" لفك تثبيت !j فقط
            elif message.startswith("فك @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_id = None
                for u, _ in room_users.content:
                    if u.username.lower() == username.lower():
                        target_id = u.id
                        break

                if target_id in self.frozen_users:
                    frozen_pos = self.frozen_users[target_id]
                    # منع فك "الزبالة" بهذا الأمر
                    if isinstance(frozen_pos, Position) and frozen_pos.x == 16.50 and frozen_pos.z == 26.50:
                         await self.highrise.chat(f"❌ عذراً @{user.username}، هذا الشخص في الزبالة! استخدم أمر (رحمتك @{username}) لفك تثبيته.")
                         return

                    # التحقق إذا كان الشخص مسجوناً، نمنع "فك" ونطلب "حرر"
                    # نستخدم موقع السجن المعروف للتحقق (16.5, 14.0, 23.5)
                    if hasattr(
                            frozen_pos, 'x'
                    ) and frozen_pos.x == 16.5 and frozen_pos.y == 14.0:
                        await self.highrise.chat(
                            f"❌ عذراً @{user.username}، هذا الشخص مسجون! استخدم أمر (حرر @{username}) لفك سجنه."
                        )
                        return

                    del self.frozen_users[target_id]
                    await self.highrise.chat(
                        f"✅ تم فك تجميد @{username} بنجاح!")
                else:
                    await self.highrise.chat(f"⚠️ @{username} ليس مثبتاً.")
                return

            # أمر هات @username لسحب المستخدم
            elif message.startswith("هات @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                sender_pos = None
                target_user = None
                for u, p in room_users.content:
                    if u.id == user.id:
                        sender_pos = p
                    if u.username.lower() == target_username.lower():
                        target_user = u
                
                if target_user:
                    # منع سحب المشرفين
                    if await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك سحب مشرف آخر!")
                        return

                    if sender_pos and isinstance(sender_pos, Position):
                        await self.highrise.teleport(target_user.id,
                                                     sender_pos)
                        await self.highrise.chat(
                            f"تم سحب {target_user.username} إليك! 🎯")
                    else:
                        await self.highrise.chat(
                            "عذراً، لا يمكنني تحديد موقعك الحالي.")
                else:
                    await self.highrise.chat(
                        f"لم أجد {target_username} في الغرفة.")
                return

            # أمر مرجح @username للطيران باللاعب
            elif message.startswith("مرجح @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = None
                for u, _ in room_users.content:
                    if u.username.lower() == target_username.lower():
                        target_user = u
                        break

                if target_user:
                    # منع مرجحة المشرفين
                    if await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك فعل ذلك بمشرف!")
                        return

                    # إذا كانت هناك مرجحة جارية، نلغيها أولاً
                    if target_user.id in self.swing_tasks:
                        self.swing_tasks[target_user.id].cancel()

                    await self.highrise.chat(
                        f"استعد للطيران يا {target_user.username}! 🎢")
                    # بدء مهمة مرجحة مستمرة في الخلفية
                    task = asyncio.create_task(self.swing_user(target_user.id))
                    self.swing_tasks[target_user.id] = task
                else:
                    await self.highrise.chat(
                        f"لم أجد {target_username} في الغرفة.")
                return

            # أمر موقعي لمعرفة الإحداثيات
            elif message.lower() == "موقعي":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                room_users = await self.highrise.get_room_users()
                user_pos = None
                for u, p in room_users.content:
                    if u.id == user.id:
                        user_pos = p
                        break

                if user_pos and isinstance(user_pos, Position):
                    coords = f"📍 إحداثيات موقعك يا @{user.username}:\n"
                    coords += f"X: {user_pos.x:.2f}\n"
                    coords += f"Y: {user_pos.y:.2f}\n"
                    coords += f"Z: {user_pos.z:.2f}\n"
                    coords += f"🧱 الاتجاه: {user_pos.facing}"
                    await self.highrise.chat(coords)
                else:
                    await self.highrise.chat(
                        "عذراً، لم أتمكن من جلب إحداثياتك.")
                return

            # أمر طلع @username لنقل المستخدم لموقع محدد
            elif message.startswith("طلع @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = next(
                    (u for u, pos in room_users.content
                     if u.username.lower() == target_username.lower()), None)
                if target_user:
                    # حماية المشرفين
                    if await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك فعل ذلك بمشرف!")
                        return
                    exit_pos = Position(10.00,
                                        0.00,
                                        11.50,
                                        facing='FrontRight')
                    await self.highrise.teleport(target_user.id, exit_pos)
                    await self.highrise.chat(
                        f"تم نقل @{target_username} إلى الخارج! 👋")
                else:
                    await self.highrise.chat(
                        f"لم أجد {target_username} في الغرفة.")
                return

            # أمر vip للذهاب لموقع محدد أو نقل شخص (للمشرفين فقط)
            elif message.startswith("vip"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                vip_pos = Position(17.50, 6.00, 13.50, facing='FrontRight')
                parts = message.split()
                if len(parts) > 1 and "@" in parts[1]:
                    # إذا كان هناك منشن، انقل الشخص الممنشن
                    target_username = parts[1].strip("@")
                    room_users = await self.highrise.get_room_users()
                    target_user = next(
                        (u for u, pos in room_users.content
                         if u.username.lower() == target_username.lower()),
                        None)
                    if target_user:
                        await self.highrise.teleport(target_user.id, vip_pos)
                        await self.highrise.chat(
                            f"تم نقل @{target_username} إلى منطقة VIP! ✨")
                    else:
                        await self.highrise.chat(
                            f"لم أجد {target_username} في الغرفة.")
                else:
                    # إذا لم يكن هناك منشن، انقل كاتب الأمر
                    await self.highrise.teleport(user.id, vip_pos)
                    await self.highrise.chat(
                        f"تم نقلك إلى منطقة VIP يا @{user.username}! ✨")

            # أمر وديني @username للذهاب لموقع مستخدم محدد
            elif message.startswith("وديني @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_pos = None
                for u, pos in room_users.content:
                    if u.username.lower() == target_username.lower():
                        target_pos = pos
                        break

                if target_pos:
                    if isinstance(target_pos, Position):
                        # نقل الشخص الذي كتب الأمر إلى موقع الهدف
                        await self.highrise.teleport(user.id, target_pos)
                        await self.highrise.chat(
                            f"تم نقلك إلى @{target_username}! ✨")
                    else:
                        await self.highrise.chat(
                            f"عذراً، لا يمكنني تحديد موقع @{target_username} بدقة."
                        )
                else:
                    await self.highrise.chat(
                        f"لم أجد {target_username} في الغرفة.")
                return

            # أمر فراغ @username لإرسال المستخدم لمكان بعيد
            elif message.startswith("فراغ @"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                target_username = message.split("@")[1].strip()
                room_users = await self.highrise.get_room_users()
                target_user = None
                for u, _ in room_users.content:
                    if u.username.lower() == target_username.lower():
                        target_user = u
                        break

                if target_user:
                    # حماية المشرفين
                    if await self.is_admin(target_user.id):
                        await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك فعل ذلك بمشرف!")
                        return
                    # إرسال المستخدم لمكان بعيد جداً (خارج حدود الغرفة المعتادة)
                    far_away_pos = Position(999, 999, 999, facing='FrontRight')
                    await self.highrise.teleport(target_user.id, far_away_pos)
                    await self.highrise.chat(
                        f"وداعاً يا {target_user.username}! 🌌")
                else:
                    await self.highrise.chat(
                        f"لم أجد {target_username} في الغرفة.")

            # أمر !go للذهاب لإحداثيات محددة
            elif message.lower() == "!go":
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                self.following_user_id = None  # التوقف عن اتباع المستخدم عند تنفيذ هذا الأمر
                target_pos = Position(6.00, 0.00, 5.50, facing='FrontRight')
                await self.highrise.walk_to(target_pos)
                await self.highrise.chat("أنا ذاهب للموقع المحدد! 🏃‍♂️")

            # أمر السبام !spam <العدد> <الرسالة>
            elif message.lower().startswith("!spam "):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                parts = message.split(maxsplit=2)
                if len(parts) >= 2:
                    try:
                        count = int(parts[1])
                        spam_text = parts[2] if len(parts) > 2 else "Spam!"
                        # إيقاف أي سبام جاري للمستخدم
                        if user.id in self.spam_tasks:
                            self.spam_tasks[user.id].cancel()

                        task = asyncio.create_task(
                            self.run_spam(user.id, count, spam_text))
                        self.spam_tasks[user.id] = task
                    except ValueError:
                        await self.highrise.chat(
                            "⚠️ يرجى إدخال رقم صحيح للكمية. مثال: !spam 5 هلا")
                else:
                    await self.highrise.chat(
                        "💡 الطريقة الصحيحة: !spam <العدد> <الرسالة>")

            # أمر إيقاف السبام !unspam أو !unspam @الاسم
            elif message.lower().startswith("!unspam"):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
                    return
                parts = message.split()
                target_user_id = None
                target_username = user.username

                if len(parts) > 1:
                    # محاولة إيقاف سبام شخص آخر
                    target_name = parts[1].strip("@")
                    room_users = await self.highrise.get_room_users()
                    target_u = next(
                        (u for u, pos in room_users.content
                         if u.username.lower() == target_name.lower()), None)
                    if target_u:
                        target_user_id = target_u.id
                        target_username = target_u.username
                    else:
                        await self.highrise.chat(
                            f"❓ لم أجد @{target_name} في الغرفة حالياً.")
                        return
                else:
                    target_user_id = user.id

                if target_user_id in self.spam_tasks:
                    self.spam_tasks[target_user_id].cancel()
                    del self.spam_tasks[target_user_id]
                    await self.highrise.chat(
                        f"⏹️ تم إيقاف السبام لـ {target_username}.")
                else:
                    if len(parts) > 1:
                        await self.highrise.chat(
                            f"💡 @{target_username} ليس لديه عمليات سبام جارية."
                        )
                    else:
                        await self.highrise.chat(
                            "💡 ليس لديك عمليات سبام جارية لإيقافها.")
                return

            # أمر !kick لطرد المستخدم من الغرفة
            elif message.startswith("!kick "):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط."
                    )
                    return
                parts = message.split()
                if len(parts) > 1:
                    # استخراج اسم المستخدم بعد علامة @
                    target_username = parts[1].strip("@")
                    # جلب قائمة المستخدمين المتواجدين في الغرفة
                    room_users = await self.highrise.get_room_users()
                    target_id = None
                    target_u_obj = None

                    # البحث عن معرف المستخدم (ID) بناءً على اسمه
                    for u, _ in room_users.content:
                        if u.username.lower() == target_username.lower():
                            target_id = u.id
                            target_u_obj = u
                            break

                    if target_id:
                        # حماية المشرفين
                        if await self.is_admin(target_id):
                            await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك طرد مشرف آخر!")
                            return
                        # تنفيذ أمر الطرد
                        await self.highrise.moderate_room(target_id, "kick")
                        await self.highrise.chat(
                            f"تم طرد {target_username} من الغرفة! 🚪")
                    else:
                        await self.highrise.chat(
                            f"لم أجد {target_username} في الغرفة.")
                else:
                    await self.highrise.chat("💡 الطريقة الصحيحة: !kick @الاسم")
                return

            # أمر !ban لحظر المستخدم من الغرفة
            elif message.startswith("!ban "):
                if not await self.is_admin(user.id):
                    await self.highrise.chat(
                        f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط."
                    )
                    return
                parts = message.split()
                if len(parts) >= 2:
                    # استخراج اسم المستخدم بعد علامة @
                    target_username = parts[1].strip("@")

                    # تحديد المدة (افتراضياً ساعة واحدة)
                    duration = 3600
                    if len(parts) > 2:
                        time_str = parts[2].lower()
                        try:
                            if time_str.endswith('m'):
                                duration = int(time_str[:-1]) * 60
                            elif time_str.endswith('h'):
                                duration = int(time_str[:-1]) * 3600
                            elif time_str.endswith('d'):
                                duration = int(time_str[:-1]) * 86400
                            elif time_str.endswith('s'):
                                duration = int(time_str[:-1])
                            else:
                                duration = int(time_str)
                        except ValueError:
                            await self.highrise.chat(
                                "⚠️ تنسيق الوقت غير صحيح. مثال: !ban @الاسم 10m"
                            )
                            return

                    # جلب قائمة المستخدمين المتواجدين في الغرفة للبحث عن المعرف (ID)
                    room_users = await self.highrise.get_room_users()
                    target_id = None
                    for u, _ in room_users.content:
                        if u.username.lower() == target_username.lower():
                            target_id = u.id
                            break

                    if target_id:
                        # حماية المشرفين
                        if await self.is_admin(target_id):
                            await self.highrise.chat(f"❌ عذراً @{user.username}، لا يمكنك حظر مشرف آخر!")
                            return
                        await self.highrise.moderate_room(
                            target_id, "ban", action_length=duration)
                        await self.highrise.chat(
                            f"تم حظر {target_username} لمدة {parts[2] if len(parts) > 2 else 'ساعة'} بنجاح! 🚫"
                        )
                    else:
                        await self.highrise.chat(
                            f"لم أجد {target_username} في الغرفة.")
                else:
                    await self.highrise.chat(
                        "💡 الطريقة الصحيحة: !ban @الاسم [المدة مثل 10m]")
                return

        except Exception as e:
            print(f"خطأ في معالجة الأمر: {e}")

    # تم حذف التكرار لضمان عمل الأوامر بشكل سليم
    async def handle_unmute(self, user: User, message: str):
        if not await self.is_admin(user.id):
            await self.highrise.chat(
                f"⚠️ عذراً @{user.username}، هذا الأمر للمشرفين فقط.")
            return
        try:
            parts = message.split()
            if len(parts) < 2: return

            target_username = parts[1].replace("@", "").strip()

            # البحث عن ID المستخدم في القائمة المحلية للمكتومين أولاً
            target_user_id = None
            if hasattr(self, 'muted_usernames'):
                target_user_id = self.muted_usernames.get(
                    target_username.lower())

            room_users = await self.highrise.get_room_users()
            target_user_in_room = next(
                (u for u, pos in room_users.content
                 if u.username.lower() == target_username.lower()), None)

            if target_user_in_room:
                target_user_id = target_user_in_room.id

            if target_user_id:
                try:
                    # محاولة إلغاء الحظر (unban) وإلغاء الكتم (unmute)
                    if message.startswith("!unban"):
                        # التحقق إذا كان المستخدم في سجلات الحظر/الكتم
                        is_banned = False
                        if hasattr(
                                self, 'muted_usernames'
                        ) and target_username.lower() in self.muted_usernames:
                            is_banned = True

                        if not is_banned:
                            await self.highrise.chat(
                                f"💡 @{target_username} ليس لديه حظر حالياً.")
                            return

                        await self.highrise.moderate_room(
                            target_user_id, "unban")
                        await self.highrise.chat(
                            f"🔓 تم إلغاء الحظر عن @{target_username} بنجاح.")
                    else:
                        # التحقق إذا كان المستخدم مكتوماً في القائمة المحلية
                        if target_user_id not in self.muted_users:
                            await self.highrise.chat(
                                f"💡 @{target_username} ليس لديه كتم حالياً.")
                            return
                        await self.highrise.moderate_room(
                            target_user_id, "mute", 1)
                        self.muted_users.discard(target_user_id)
                        await self.highrise.chat(
                            f"🔊 تم إلغاء الكتم عن @{target_username} بنجاح.")

                    if hasattr(self, 'muted_usernames'):
                        keys_to_del = [
                            k for k, v in self.muted_usernames.items()
                            if v == target_user_id
                        ]
                        for k in keys_to_del:
                            del self.muted_usernames[k]

                except Exception as inner:
                    print(f"⚠️ خطأ أثناء إلغاء الحظر/الكتم: {inner}")
            else:
                await self.highrise.chat(
                    f"❓ لم أجد @{target_username} في السجلات أو الغرفة.")
        except Exception as e:
            print(f"❌ فشل أمر إلغاء الحظر/الكتم: {e}")

    async def on_tip(self, sender: User, receiver: User,
                     tip: CurrencyItem | Item) -> None:
        print(
            f"{sender.username} tipped {receiver.username} an amount of {tip.amount}"
        )

        # ميزات الـ Tips المضافة:
        try:
            # 1. شكر مرسل الذهب في الشات العام
            await self.highrise.chat(
                f"شكرا لك على قولد @{sender.username} تبرعت بـ {tip.amount}")

            # 2. تفاعل (قلوب) للشخص الذي أرسل الذهب
            for _ in range(5):
                await self.highrise.react("heart", sender.id)
                await asyncio.sleep(0.1)

            # 3. إذا كان الذهب مرسل للبوت نفسه (يمكنك تخصيص رد فعل خاص)
            bot_info = await self.highrise.me()
            if receiver.id == bot_info.id:
                await self.highrise.send_whisper(
                    sender.id,
                    "💖 شكراً جزيلاً على دعمك لي! يسعدني خدمتك دائماً.")
                # رقصة خاصة تعبيراً عن الشكر
                await self.highrise.send_emote("emote-kissing", sender.id)

        except Exception as e:
            print(f"خطأ في ميزات الـ Tips: {e}")

    async def on_user_out(self, user: User) -> None:
        """يتم استدعاء هذه الدالة عندما يغادر لاعب الغرفة (بما في ذلك الطرد)"""
        try:
            # التحقق من سجلات الإشراف (Moderation Logs) لمعرفة من قام بطرد اللاعب
            # ملاحظة: SDK قد لا يوفر الحدث مباشرة، لذا سنستخدم on_moderation_event إذا كان مدعوماً
            pass
        except Exception as e:
            print(f"خطأ في حدث خروج المستخدم: {e}")

    async def on_moderation_event(self,
                                  user_id: str,
                                  event: str,
                                  moderator_id: str,
                                  duration: int = 1) -> None:
        """يتم استدعاء هذه الدالة عند حدوث فعل إشرافي (طرد، حظر، كتم)"""
        try:
            if event in ["kick", "ban"]:
                # محاولة الحصول على أسماء المستخدمين
                room_users = await self.highrise.get_room_users()
                moderator_name = moderator_id
                target_name = user_id
                target_owner_id = None

                for u, _ in room_users.content:
                    if u.id == moderator_id:
                        moderator_name = u.username
                    if u.id == user_id:
                        target_name = u.username
                    if u.username.lower() == "_7rbi":
                        target_owner_id = u.id

                action_name = "طرد" if event == "kick" else "حظر"
                log_msg = f"📢 تنبيه: قام المشرف @{moderator_name} بـ {action_name} اللاعب @{target_name} 🚫"

                # إرسال الهمس مباشرة إذا وجدنا ID صاحب البوت
                if target_owner_id:
                    await self.highrise.send_whisper(target_owner_id, log_msg)
                else:
                    # إذا لم يكن في الغرفة، نحاول البحث عنه مرة أخرى للتأكد
                    for u, _ in room_users.content:
                        if u.username.lower() == "_7rbi":
                            await self.highrise.send_whisper(u.id, log_msg)
                            break

        except Exception as e:
            print(f"خطأ في إرسال تنبيه الهمس: {e}")

    async def swing_user(self, user_id: str):
        """دالة للقيام بالمرجحة المستمرة بأماكن أبعد وأقوى"""
        try:
            while True:
                random_pos = Position(random.uniform(-30, 60),
                                      random.uniform(0, 40),
                                      random.uniform(-30, 60),
                                      facing='FrontRight')
                await self.highrise.teleport(user_id, random_pos)
                await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"خطأ في مهمة المرجحة: {e}")

    async def run_spam(self, user_id: str, count: int, text: str):
        """دالة للقيام بالسبام في الخلفية للسماح بإيقافه"""
        try:
            # تحديد حد أقصى للسبام لتجنب الحظر
            count = min(count, 100)
            for _ in range(count):
                await self.highrise.chat(text)
                await asyncio.sleep(0.5)
            if user_id in self.spam_tasks:
                del self.spam_tasks[user_id]
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"خطأ في مهمة السبام: {e}")

    # تم حذف التكرار هنا لضمان عمل الأوامر بشكل صحيح


import sys
import os

if __name__ == "__main__":
    import subprocess
    import sys

    # جلب القيم من الأسرار أو البيئة
    room_id = os.environ.get("ROOM_ID") or os.environ.get(
        "HIGHRISE_ROOM_ID") or "6950358f6bf0ec2d5ecc0e3e"
    bot_token = os.environ.get("API_TOKEN") or os.environ.get(
        "HIGHRISE_API_TOKEN"
    ) or "a50ebcefdf5c5a307464c0e3bc45b438b209fe8995a22c4a573b86b571affacf"
    bot_file = "main:WelcomeBot"

    # تشغيل البوت باستخدام أمر الـ CLI الخاص بـ SDK لضمان التوافق
    print(f"جاري تشغيل البوت في الغرفة: {room_id}")
    subprocess.run(
        [sys.executable, "-m", "highrise", bot_file, room_id, bot_token])
