#!/usr/bin/env python3
"""Add native Persian (fa) translations to exercises.json alongside English."""

import json
import csv
import re
import sys

# ── 1. Load CSV mappings ──────────────────────────────────────────────────
csv_map = {}
with open("data/Persian_Fitness_Exercises_Dataset.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        en = row.get("نام انگلیسی (English Name)", "").strip().lower()
        fa = row.get("نام حرکت (Exercise Name)", "").strip()
        if en and fa:
            csv_map[en] = fa

exercises = json.load(open("exercises.json"))

# ── 2. Metadata translation dictionaries ─────────────────────────────────

category_fa = {
    "back": "پشت",
    "cardio": "هوازی",
    "chest": "سینه",
    "lower arms": "ساعد",
    "lower legs": "ساق پا",
    "neck": "گردن",
    "shoulders": "سرشانه",
    "upper arms": "بازو",
    "upper legs": "پا",
    "waist": "شکم و پهلو",
}

body_part_fa = {
    "back": "پشت",
    "cardio": "قلبی عروقی",
    "chest": "سینه",
    "lower arms": "ساعد",
    "lower legs": "ساق پا",
    "neck": "گردن",
    "shoulders": "سرشانه",
    "upper arms": "بازو",
    "upper legs": "پایین تنه",
    "waist": "شکم",
}

equipment_fa = {
    "assisted": "دستگاه کمکی",
    "band": "کش ورزشی",
    "barbell": "هالتر",
    "body weight": "وزن بدن",
    "bosu ball": "توپ بوسو",
    "cable": "سیم‌کش",
    "dumbbell": "دمبل",
    "elliptical machine": "الپتیکال",
    "ez barbell": "هالتر ئی‌زی",
    "hammer": "پتک",
    "kettlebell": "کتل‌بل",
    "leverage machine": "دستگاه اهرم‌دار",
    "medicine ball": "توپ پزشکی",
    "olympic barbell": "هالتر المپیکی",
    "resistance band": "کش مقاومتی",
    "roller": "غلتک",
    "rope": "طناب",
    "skierg machine": "دستگاه اسکی‌ارگ",
    "sled machine": "دستگاه سورتمه",
    "smith machine": "اسمیت",
    "stability ball": "توپ تعادلی",
    "stationary bike": "دوچرخه ثابت",
    "stepmill machine": "استپ میل",
    "tire": "لاستیک",
    "trap bar": "میله ترپ",
    "upper body ergometer": "ارگومتر بالاتنه",
    "weighted": "وزنه‌دار",
    "wheel roller": "غلتک شکم",
}

muscle_group_fa = {
    "abdominals": "شکم",
    "ankle stabilizers": "تثبیت‌کننده‌های مچ پا",
    "ankles": "مچ پا",
    "back": "پشت",
    "biceps": "جلو بازو",
    "brachialis": "براکیالیس",
    "calves": "ساق پا",
    "chest": "سینه",
    "core": "هسته بدن",
    "deltoids": "دلتوئید",
    "feet": "پاها",
    "forearms": "ساعد",
    "glutes": "باسن",
    "grip muscles": "عضلات پنجه",
    "groin": "کشاله ران",
    "hamstrings": "پشت ران",
    "hands": "دست‌ها",
    "hip flexors": "خم‌کننده‌های لگن",
    "inner thighs": "داخل ران",
    "latissimus dorsi": "پشتی بزرگ",
    "lats": "زیربغل",
    "lower abs": "زیرشکم",
    "lower back": "کمر",
    "obliques": "پهلو",
    "quadriceps": "چهارسر ران",
    "rear deltoids": "دلتوئید خلفی",
    "rhomboids": "رومبوئیدها",
    "rotator cuff": "کلاهک چرخاننده",
    "shins": "ساق",
    "shoulders": "سرشانه",
    "soleus": "سولئوس",
    "sternocleidomastoid": "جناغی‌چنبری‌پستانی",
    "trapezius": "ذوزنقه‌ای",
    "traps": "کول",
    "triceps": "پشت بازو",
    "upper back": "بالای کمر",
    "upper chest": "بالای سینه",
    "wrist extensors": "بازکننده‌های مچ",
    "wrist flexors": "خم‌کننده‌های مچ",
    "wrists": "مچ‌ها",
}

target_fa = {
    "abductors": "دورکننده‌ها",
    "abs": "شکم",
    "adductors": "نزدیک‌کننده‌ها",
    "biceps": "جلو بازو",
    "calves": "ساق پا",
    "cardiovascular system": "سیستم قلبی عروقی",
    "delts": "دلتوئید",
    "forearms": "ساعد",
    "glutes": "باسن",
    "hamstrings": "پشت ران",
    "lats": "زیربغل",
    "levator scapulae": "بالابرنده کتف",
    "pectorals": "سینه",
    "quads": "چهارسر ران",
    "serratus anterior": "دنده‌ای قدامی",
    "spine": "ستون فقرات",
    "traps": "کول",
    "triceps": "پشت بازو",
    "upper back": "بالای کمر",
}

# ── 3. Exercise name translation ────────────────────────────────────────

# Component dictionary for constructing Persian exercise names
name_components = {
    "3/4": "سه‌چهارم",
    "45°": "۴۵ درجه",
    "90°": "۹۰ درجه",
    "180°": "۱۸۰ درجه",
    "abduction": "دور کردن",
    "adduction": "نزدیک کردن",
    "adductor": "نزدیک‌کننده",
    "air bike": "دوچرخه هوایی",
    "alternate": "تناوبی",
    "alternating": "تناوبی",
    "ankle": "مچ پا",
    "archer": "کمانی",
    "arm": "دست",
    "arms": "دست‌ها",
    "arnold press": "پرس آرنولدی",
    "assisted": "کمکی",
    "back extension": "فیله کمر",
    "back squat": "اسکوات پشت",
    "backward": "عقب",
    "balance": "تعادل",
    "ball": "توپ",
    "band": "کش",
    "barbell": "هالتر",
    "bear crawl": "خرس",
    "behind": "پشت",
    "bench": "میز",
    "bench dip": "دیپ میز",
    "bench press": "پرس سینه",
    "bent knee": "زانو خم",
    "bent over": "خم",
    "biceps": "جلو بازو",
    "bicycle": "دوچرخه",
    "bird dog": "پرنده و سگ",
    "block": "بلوک",
    "body weight": "وزن بدن",
    "bosu ball": "بوسو",
    "both": "جفت",
    "box": "جعبه",
    "box squat": "باکس اسکوات",
    "bridge": "پل",
    "broad jump": "پرش طولی",
    "bulgarian": "بلغاری",
    "burpee": "برپی",
    "butt kick": "ضربه به باسن",
    "cable": "سیم‌کش",
    "calf": "ساق پا",
    "calves": "ساق پا",
    "captain's chair": "صندلی کاپیتان",
    "carry": "حمل",
    "cat cow": "گربه و گاو",
    "chair": "صندلی",
    "chest": "سینه",
    "chest dip": "دیپ سینه",
    "chin-up": "بارفیکس مچ برعکس",
    "chin up": "بارفیکس مچ برعکس",
    "circle": "دایره",
    "circular": "دایره‌ای",
    "clam": "صدفی",
    "clean": "کلین",
    "clean and jerk": "کلین و جرک",
    "close grip": "دست جمع",
    "cobra": "کبری",
    "concentration": "تمرکزی",
    "conventional": "کلاسیک",
    "cossack squat": "اسکوات قزاقی",
    "crab walk": "راه رفتن خرچنگی",
    "cross": "ضربدری",
    "cross body": "ضربدری",
    "crunch": "کرانچ",
    "curl": "جلو بازو",
    "curtsy": "ادب",
    "dead bug": "سوسک مرده",
    "deadlift": "ددلیفت",
    "decline": "شیب منفی",
    "deep": "عمیق",
    "deltoid": "دلتوئید",
    "dip": "دیپ",
    "donkey": "الاغی",
    "donkey kick": "ضربه الاغ",
    "double": "دو",
    "downward dog": "سگ سر پایین",
    "dumbbell": "دمبل",
    "dynamic": "پویا",
    "eccentric": "اکسنتریک",
    "elliptical": "الپتیکال",
    "explosive": "انفجاری",
    "extension": "باز شدن",
    "external": "خارجی",
    "ez bar": "هالتر ئی‌زی",
    "ez barbell": "هالتر ئی‌زی",
    "face down": "دمر",
    "face pull": "فیس پول",
    "farmer": "کشاورز",
    "fire hydrant": "شیر آتش‌نشانی",
    "flat": "تخت",
    "flexion": "خم شدن",
    "flutter kick": "ضربه قیچی",
    "fly": "قفسه",
    "flying": "پروازی",
    "forward": "جلو",
    "forward fold": "خم به جلو",
    "french press": "فرانسوی",
    "frog": "قورباغه",
    "front": "جلو",
    "front raise": "نشر از جلو",
    "front squat": "اسکوات جلو",
    "full": "کامل",
    "glute bridge": "پل باسن",
    "glute": "باسن",
    "glutes": "باسن",
    "goblet": "گابلت",
    "good morning": "صبح بخیر",
    "grip": "گیره",
    "groiner": "کشاله",
    "hack squat": "اسکوات هاک",
    "half": "نیمه",
    "hammer": "چکشی",
    "hamstring": "پشت ران",
    "hamstrings": "پشت ران",
    "hand": "دست",
    "handstand": "ایستادن روی دست",
    "hang": "آویزان",
    "hanging": "آویزان",
    "happy baby": "نوزاد خوشحال",
    "heel touch": "لمس پاشنه",
    "high knee": "زانوی بلند",
    "hip": "لگن",
    "hip adduction": "نزدیک کردن پا",
    "hip abduction": "دور کردن پا",
    "hip extension": "باز کردن لگن",
    "hip flexor": "خم‌کننده لگن",
    "hip hinge": "لولای لگن",
    "hip lift": "بالا آوردن لگن",
    "hip thrust": "هیپ تراست",
    "hold": "ایستا",
    "hop": "لی",
    "hyperextension": "هایپراکستنشن",
    "incline": "شیب‌دار",
    "inner thigh": "داخل ران",
    "inside": "داخلی",
    "internal": "داخلی",
    "isometric": "ایزومتریک",
    "jack knife": "جک نایف",
    "jerk": "جرک",
    "jog": "دویدن",
    "jump": "پرش",
    "jumping jack": "جامپینگ جک",
    "kettlebell": "کتل‌بل",
    "kick": "ضربه",
    "kickback": "کیک بک",
    "knee": "زانو",
    "kneeling": "زانو زده",
    "landmine": "لندماین",
    "lateral": "از جانب",
    "lateral raise": "نشر از جانب",
    "lat pulldown": "لت",
    "lean": "خم",
    "leg": "پا",
    "leg curl": "پشت ران",
    "leg extension": "جلو ران",
    "leg press": "پرس پا",
    "leg raise": "بالا آوردن پا",
    "leverage": "اهرمی",
    "lift": "بلند کردن",
    "lizard": "مارمولک",
    "locust": "ملخ",
    "low row": "قایقی",
    "lower": "پایین",
    "lunge": "لانچ",
    "lying": "خوابیده",
    "machine": "دستگاه",
    "medicine ball": "توپ پزشکی",
    "military press": "پرس نظامی",
    "mountain climber": "کوهنورد",
    "narrow": "جمع",
    "neck": "گردن",
    "oblique": "پهلو",
    "olympic": "المپیکی",
    "one arm": "تک دست",
    "one hand": "تک دست",
    "on back": "به پشت",
    "on side": "به پهلو",
    "outside": "خارجی",
    "overhead": "بالای سر",
    "pallof press": "پالوف پرس",
    "pec deck": "پک دک",
    "pectoral": "سینه‌ای",
    "pelvic": "لگنی",
    "pendlay row": "پارو پندلی",
    "pigeon": "کبوتر",
    "pike": "پایک",
    "pistol": "تک پا",
    "plank": "پلانک",
    "plate": "صفحه",
    "plyometric": "پلایومتریک",
    "power": "قدرتی",
    "power clean": "پاور کلین",
    "preacher": "لاری",
    "press": "پرس",
    "prone": "دمر",
    "pull": "کشیدن",
    "pull up": "بارفیکس",
    "pull-up": "بارفیکس",
    "pulldown": "لت",
    "pullover": "پلاور",
    "push": "فشار",
    "push press": "پوش پرس",
    "push up": "شنا",
    "push-up": "شنا",
    "quad": "چهارسر ران",
    "raise": "نشر",
    "rear": "خلفی",
    "rear delt": "دلتوئید خلفی",
    "resistance band": "کش مقاومتی",
    "reverse": "معکوس",
    "reverse crunch": "کرانچ معکوس",
    "romanian": "رومانیایی",
    "rope": "طناب",
    "rotation": "چرخش",
    "rotator cuff": "کلاهک چرخاننده",
    "row": "قایقی",
    "rowing": "قایقرانی",
    "russian twist": "شکم روسی",
    "seated": "نشسته",
    "shoulder": "سرشانه",
    "shoulder press": "پرس سرشانه",
    "shrug": "شراگ",
    "side": "پهلو",
    "side bend": "خم پهلو",
    "side plank": "پلانک پهلو",
    "single": "تک",
    "single leg": "تک پا",
    "sit-up": "دراز و نشست",
    "sit up": "دراز و نشست",
    "skater": "اسکیت",
    "skip": "پرش",
    "skull crusher": "فرانسوی",
    "sled": "سورتمه",
    "smith machine": "اسمیت",
    "snatch": "یک ضرب",
    "speed": "سرعتی",
    "spider": "عنکبوتی",
    "split squat": "اسپلیت اسکوات",
    "squat": "اسکوات",
    "stability ball": "توپ تعادلی",
    "standing": "ایستاده",
    "static": "ایستا",
    "stationary": "ثابت",
    "step": "استپ",
    "step-up": "استپ",
    "stirrup": "رکابی",
    "straight": "صاف",
    "straight arm": "دست صاف",
    "straight leg": "پا صاف",
    "stretch": "کشش",
    "suitcase": "چمدانی",
    "sumo": "سومو",
    "superman": "سوپرمن",
    "swing": "تاب",
    "t-bar row": "تی بار",
    "thruster": "تراستر",
    "toe touch": "لمس انگشت پا",
    "torso": "تنه",
    "towel": "حوله",
    "trap bar": "میله ترپ",
    "treadmill": "تردمیل",
    "tree pose": "درخت",
    "triangle": "مثلث",
    "triceps": "پشت بازو",
    "trunk": "تنه",
    "twist": "چرخش",
    "twisted": "چرخیده",
    "upward dog": "سگ سر بالا",
    "upright row": "کول",
    "v-up": "وی‌آپ",
    "v up": "وی‌آپ",
    "walk": "راه رفتن",
    "walking": "راه رفتن",
    "wall": "دیوار",
    "wall sit": "نشستن روی دیوار",
    "warrior": "جنگجو",
    "wheel": "چرخ",
    "wheel roller": "غلتک",
    "wide grip": "دست باز",
    "wood chop": "هیلکات",
    "wrist": "مچ",
    "wrist curl": "مچ",
    # Fitness-specific prefixes
    "assisted": "کمکی",
    "weighted": "وزنه‌دار",
    "banded": "کش دار",
    "cable": "سیم‌کش",
    "bodyweight": "وزن بدن",
}


def translate_exercise_name(en_name: str) -> str:
    """Translate exercise name to Persian using CSV + component approach."""
    key = en_name.strip().lower()

    # 1. Check CSV first
    if key in csv_map:
        return csv_map[key]

    # 2. Check direct component lookup
    if key in name_components:
        return name_components[key]

    # 3. Component-based translation
    # Remove (male) / (female) suffixes
    cleaned = re.sub(r"\s*\(male\)\s*", "", key, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\(female\)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    # Try component matching
    parts = cleaned.split()
    translated_parts = []
    skip = False
    for i, part in enumerate(parts):
        if skip:
            skip = False
            continue
        # Multi-word check
        if i + 1 < len(parts):
            two = f"{part} {parts[i+1]}"
            if two in name_components:
                translated_parts.append(name_components[two])
                skip = True
                continue
        part_clean = part.strip(".,-‑")
        if part_clean in name_components:
            translated_parts.append(name_components[part_clean])
        else:
            # Keep numbers, degrees, etc.
            translated_parts.append(part_clean)

    result = " ".join(translated_parts)

    # Fallback: if nothing translated, return key as-is
    if not result or result == cleaned:
        # Try exact name components
        return en_name  # fallback — will be reviewed

    return result


# ── 4. Instruction / sentence translation ───────────────────────────────

verb_fa = {
    "abduct": "دور کنید",
    "abducting": "دور کردن",
    "adduct": "نزدیک کنید",
    "adducting": "نزدیک کردن",
    "adjust": "تنظیم کنید",
    "allow": "اجازه دهید",
    "arch": "قوس دهید",
    "attach": "متصل کنید",
    "balance": "تعادل بگیرید",
    "begin": "شروع کنید",
    "bend": "خم کنید",
    "bending": "خم کردن",
    "bring": "بیاورید",
    "clasp": "قلاب کنید",
    "contract": "منقبض کنید",
    "contracting": "منقبض کردن",
    "cross": "ضربدری کنید",
    "curl": "حلقه کنید",
    "do": "انجام دهید",
    "drive": "هل دهید",
    "drop": "رها کنید",
    "elevate": "بالا ببرید",
    "engage": "درگیر کنید",
    "engaging": "درگیر کردن",
    "execute": "اجرا کنید",
    "extend": "صاف کنید",
    "extending": "صاف کردن",
    "feel": "احساس کنید",
    "feeling": "احساس",
    "flex": "خم کنید",
    "flexing": "خم کردن",
    "focus": "تمرکز کنید",
    "grab": "بگیرید",
    "grasp": "بگیرید",
    "grip": "بگیرید",
    "hang": "آویزان شوید",
    "hold": "نگه دارید",
    "holding": "نگه داشتن",
    "interlock": "قلاب کنید",
    "keep": "نگه دارید",
    "keeping": "نگه داشتن",
    "kneel": "زانو بزنید",
    "land": "فرود بیایید",
    "lean": "خم شوید",
    "lift": "بلند کنید",
    "lifting": "بلند کردن",
    "lie": "دراز بکشید",
    "lock": "قفل کنید",
    "lower": "پایین بیاورید",
    "lowering": "پایین آوردن",
    "maintain": "حفظ کنید",
    "maintaining": "حفظ",
    "pause": "مکث کنید",
    "perform": "اجرا کنید",
    "place": "قرار دهید",
    "position": "قرار دهید",
    "press": "فشار دهید",
    "pull": "بکشید",
    "pulling": "کشیدن",
    "push": "فشار دهید",
    "pushing": "فشار دادن",
    "put": "بگذارید",
    "raise": "بلند کنید",
    "raising": "بلند کردن",
    "reach": "برسانید",
    "release": "رها کنید",
    "repeat": "تکرار کنید",
    "resist": "مقاومت کنید",
    "resisting": "مقاومت",
    "rest": "قرار دهید",
    "return": "بازگردید",
    "roll": "بغلتانید",
    "rotate": "بچرخانید",
    "rotating": "چرخاندن",
    "secure": "محکم کنید",
    "set": "تنظیم کنید",
    "shift": "انتقال دهید",
    "sit": "بنشینید",
    "squeeze": "منقبض کنید",
    "squeezing": "منقبض کردن",
    "stand": "بایستید",
    "start": "شروع کنید",
    "step": "قدم بردارید",
    "straighten": "صاف کنید",
    "straightening": "صاف کردن",
    "switch": "عوض کنید",
    "swing": "تاب دهید",
    "tilt": "کج کنید",
    "tuck": "جمع کنید",
    "tucking": "جمع کردن",
    "turn": "بچرخانید",
    "twist": "بچرخانید",
    "twisting": "چرخاندن",
    "walk": "راه بروید",
    "wrap": "حلقه کنید",
}

body_part_fa_instr = {
    "abs": "شکم",
    "abdominals": "شکم",
    "ankle": "مچ پا",
    "ankles": "مچ‌های پا",
    "arch": "قوس پا",
    "arm": "بازو",
    "arms": "بازوها",
    "back": "کمر",
    "biceps": "جلو بازو",
    "body": "بدن",
    "calf": "ساق",
    "calves": "ساق پا",
    "chest": "سینه",
    "chin": "چانه",
    "core": "هسته بدن",
    "ear": "گوش",
    "ears": "گوش‌ها",
    "elbow": "آرنج",
    "elbows": "آرنج‌ها",
    "feet": "کف پا",
    "finger": "انگشت",
    "fingers": "انگشتان",
    "foot": "پا",
    "forearm": "ساعد",
    "forearms": "ساعدها",
    "glute": "باسن",
    "glutes": "باسن",
    "hamstring": "پشت ران",
    "hamstrings": "پشت ران",
    "hand": "دست",
    "hands": "دست‌ها",
    "head": "سر",
    "heel": "پاشنه",
    "heels": "پاشنه‌ها",
    "hip": "لگن",
    "hips": "لگن",
    "knee": "زانو",
    "knees": "زانوها",
    "lats": "زیربغل",
    "leg": "پا",
    "legs": "پاها",
    "lower back": "کمر",
    "neck": "گردن",
    "obliques": "پهلو",
    "palm": "کف دست",
    "palms": "کف دست‌ها",
    "pectorals": "سینه",
    "quad": "چهارسر ران",
    "quads": "چهارسر ران",
    "quadriceps": "چهارسر ران",
    "ribcage": "قفسه سینه",
    "ribs": "دنده‌ها",
    "shin": "ساق",
    "shins": "ساق",
    "shoulder": "شانه",
    "shoulders": "شانه‌ها",
    "spine": "ستون فقرات",
    "stomach": "شکم",
    "thigh": "ران",
    "thighs": "ران‌ها",
    "toe": "انگشت پا",
    "toes": "انگشتان پا",
    "torso": "تنه",
    "traps": "کول",
    "triceps": "پشت بازو",
    "waist": "کمر",
    "wrist": "مچ",
    "wrists": "مچ‌ها",
}

equip_fa_instr = {
    "band": "کش",
    "bands": "کش‌ها",
    "barbell": "هالتر",
    "bench": "میز",
    "cable machine": "سیم‌کش",
    "cable": "سیم‌کش",
    "chair": "صندلی",
    "dumbbell": "دمبل",
    "dumbbells": "دمبل‌ها",
    "exercise ball": "توپ ورزشی",
    "handle": "دسته",
    "handles": "دسته‌ها",
    "kettlebell": "کتل‌بل",
    "kettlebells": "کتل‌بل‌ها",
    "machine": "دستگاه",
    "mat": "مت",
    "medicine ball": "توپ پزشکی",
    "pad": "پد",
    "pull-up bar": "میله بارفیکس",
    "resistance band": "کش مقاومتی",
    "rope": "طناب",
    "stability ball": "توپ تعادلی",
    "step": "استپ",
    "towel": "حوله",
    "weight": "وزنه",
    "wheel": "غلتک",
}

adj_fa = {
    "bent": "خم",
    "extended": "صاف",
    "flexed": "خم",
    "locked": "قفل",
    "straight": "صاف",
    "flat": "تخت",
    "upright": "عمودی",
    "parallel": "موازی",
    "perpendicular": "عمود",
    "shoulder-width": "به اندازه عرض شانه",
    "hip-width": "به اندازه عرض لگن",
    "elevated": "بالا",
    "raised": "بلند",
}

direction_fa = {
    "apart": "جدا",
    "away": "دور",
    "back": "عقب",
    "backward": "عقب",
    "down": "پایین",
    "downward": "پایین",
    "forward": "جلو",
    "front": "جلو",
    "in": "داخل",
    "inward": "داخل",
    "out": "بیرون",
    "outward": "بیرون",
    "side": "پهلو",
    "sideways": "پهلو",
    "together": "جفت",
    "up": "بالا",
    "upward": "بالا",
}

prep_fa = {
    "above": "بالای",
    "across": "عرض",
    "against": "به",
    "around": "دور",
    "at": "در",
    "behind": "پشت",
    "between": "بین",
    "by": "کنار",
    "down": "پایین",
    "from": "از",
    "in": "در",
    "in front of": "جلوی",
    "into": "به",
    "on": "روی",
    "out of": "از",
    "over": "بالای",
    "through": "از",
    "to": "به",
    "toward": "به سمت",
    "towards": "به سمت",
    "under": "زیر",
    "up": "بالا",
    "with": "با",
}

time_fa = {
    "moment": "لحظه",
    "second": "ثانیه",
    "seconds": "ثانیه",
}

num_fa = {
    "one": "یک",
    "two": "دو",
    "three": "سه",
    "four": "چهار",
    "five": "پنج",
    "six": "شش",
    "seven": "هفت",
    "eight": "هشت",
    "nine": "نه",
    "ten": "ده",
    "a": "یک",
    "each": "هر",
    "both": "هر دو",
    "other": "دیگر",
    "same": "همان",
    "opposite": "مقابل",
    "desired": "دلخواه",
    "several": "چند",
    "your": "",
}


def translate_instruction_sentence(sentence: str) -> str:
    """Translate a single instruction sentence to Persian."""
    s = sentence.strip()

    # ── Handle common full-sentence patterns ──

    # "Repeat for the desired number of repetitions."
    if re.match(r"repeat for the desired number of repetitions\.?", s, re.I):
        return "این حرکت را برای تعداد تکرار دلخواه خود انجام دهید."

    # "Repeat for the desired number of repetitions on each side."
    if re.match(r"repeat for the desired number of repetitions on each side\.?", s, re.I):
        return "این حرکت را برای تعداد تکرار دلخواه در هر طرف انجام دهید."

    # "Continue alternating sides for the desired number of repetitions."
    if re.match(r"continue alternating sides for the desired number of repetitions\.?", s, re.I):
        return "به طور متناوب بین طرف‌ها برای تعداد تکرار دلخواه خود ادامه دهید."

    # "Continue alternating sides for the desired number of repetitions on each side."
    if re.match(
        r"continue alternating sides for the desired number of repetitions on each side\.?", s, re.I
    ):
        return "به طور متناوب بین طرف‌ها برای تعداد تکرار دلخواه در هر طرف ادامه دهید."

    # "Switch legs and repeat the stretch on the other side."
    if re.match(r"switch legs and repeat the stretch on the other side\.?", s, re.I):
        return "پاها را عوض کنید و کشش را در طرف دیگر تکرار کنید."

    # "Release and repeat on the other side."
    if re.match(r"release and repeat on the other side\.?", s, re.I):
        return "رها کنید و در طرف دیگر تکرار کنید."

    # "Release the stretch and repeat on the other side."
    if re.match(r"release the stretch and repeat on the other side\.?", s, re.I):
        return "کشش را رها کنید و در طرف دیگر تکرار کنید."

    # "Hold for 20-30 seconds."
    if re.match(r"hold for \d+[-–]\d+ seconds?\.?", s, re.I):
        return "این حالت را برای ۲۰ تا ۳۰ ثانیه نگه دارید."

    # "Hold this position for 20-30 seconds."
    if re.match(r"hold this position for \d+[-–]\d+ seconds?\.?", s, re.I):
        return "این وضعیت را برای ۲۰ تا ۳۰ ثانیه نگه دارید."

    # "Hold the stretch for 20-30 seconds."
    if re.match(r"hold the stretch for \d+[-–]\d+ seconds?\.?", s, re.I):
        return "کشش را برای ۲۰ تا ۳۰ ثانیه نگه دارید."

    # "Hold for a moment at the top"
    # Already covered by pause pattern below

    # "Release the stretch and repeat on the other leg."
    if re.match(r"release the stretch and repeat on the other leg\.?", s, re.I):
        return "کشش را رها کنید و با پای دیگر تکرار کنید."

    # "Repeat on the other side."
    if re.match(r"repeat on the other side\.?", s, re.I):
        return "در طرف دیگر تکرار کنید."

    # "Repeat on the other leg."
    if re.match(r"repeat on the other leg\.?", s, re.I):
        return "با پای دیگر تکرار کنید."

    # "Repeat with the other leg."
    if re.match(r"repeat with the other leg\.?", s, re.I):
        return "با پای دیگر تکرار کنید."

    # ── Pause patterns ──
    # "Pause for a moment at the top, then slowly lower back down."
    m = re.match(
        r"pause for a moment at the (top|bottom|peak|peak of the movement),?\s*(and)?\s*then (slowly )?(lower|release|return|raise|lift|push|pull)\b",
        s,
        re.I,
    )
    if m:
        pos = m.group(1)
        verb = m.group(4).lower()
        direction = ""
        if "lower" in s or "release" in s:
            direction = "پایین"
        elif "raise" in s or "lift" in s:
            direction = "بالا"
        elif "return" in s:
            return "لحظه‌ای در نقطه اوج مکث کنید، سپس به آرامی به وضعیت شروع بازگردید."
        elif "push" in s:
            direction = "بازگشت"
        elif "pull" in s:
            direction = "بالا"

        pos_fa = {
            "top": "بالا",
            "bottom": "پایین",
            "peak": "اوج",
            "peak of the movement": "اوج حرکت",
        }.get(pos, pos)
        return f"لحظه‌ای در {pos_fa} مکث کنید، سپس به آرامی {direction} بیاورید."

    # ── General pause pattern ──
    if re.match(r"pause for a moment at the", s, re.I):
        return s.replace("Pause for a moment at the", "لحظه‌ای در")

    # ── Word-by-word translation approach ──
    return translate_sentence_wordwise(s)


def translate_sentence_wordwise(sentence: str) -> str:
    """Translate a sentence word-by-word with Persian grammar adjustments."""
    s = sentence.strip()

    # Remove trailing period for processing
    end_period = s.endswith(".")
    s_clean = s.rstrip(".!")

    words = s_clean.split()
    if not words:
        return ""

    first_word = words[0].lower()

    result_parts = []

    # Handle common sentence starters
    if first_word in verb_fa:
        verb = verb_fa[first_word]
        rest = " ".join(words[1:])
        translated_rest = translate_phrase(rest)
        # Persian word order: [rest] [verb]
        if translated_rest:
            result_parts.append(translated_rest)
        result_parts.append(verb)
    else:
        # No matching verb start, translate as phrase
        result_parts.append(translate_phrase(s_clean))

    result = " ".join(result_parts).strip()
    if end_period:
        result += "."

    return result


def translate_phrase(phrase: str) -> str:
    """Translate a phrase using word-by-word lookup."""
    if not phrase.strip():
        return ""

    words = phrase.split()
    translated = []
    skip = False

    for i, w in enumerate(words):
        if skip:
            skip = False
            continue
        w_lower = w.lower().strip(",.()[]!?;-‑")

        # Multi-word check
        if i + 1 < len(words):
            two = f"{w_lower} {words[i+1].lower().strip(',.()[]!?;-‑')}"
            if two in body_part_fa_instr:
                translated.append(body_part_fa_instr[two])
                skip = True
                continue
            if two in prep_fa:
                translated.append(prep_fa[two])
                skip = True
                continue
            if two in equip_fa_instr:
                translated.append(equip_fa_instr[two])
                skip = True
                continue
            # shoulder-width, hip-width patterns
            if w_lower in ("shoulder", "hip") and words[i + 1].lower().strip() == "width":
                if w_lower == "shoulder":
                    translated.append("به اندازه عرض شانه")
                else:
                    translated.append("به اندازه عرض لگن")
                skip = True
                continue
            # "back down" as a unit
            if w_lower == "back" and words[i + 1].lower().strip() == "down":
                skip = True
                continue

        # Single word lookups
        if w_lower in body_part_fa_instr:
            translated.append(body_part_fa_instr[w_lower])
        elif w_lower in verb_fa:
            # Verbs in the middle get conjugated to past stem form
            v = verb_fa[w_lower]
            translated.append(v)
        elif w_lower in equip_fa_instr:
            translated.append(equip_fa_instr[w_lower])
        elif w_lower in direction_fa:
            translated.append(direction_fa[w_lower])
        elif w_lower in adj_fa:
            translated.append(adj_fa[w_lower])
        elif w_lower in num_fa:
            translated.append(num_fa[w_lower])
        elif w_lower in prep_fa:
            translated.append(prep_fa[w_lower])
        elif w_lower in time_fa:
            translated.append(time_fa[w_lower])
        elif w_lower.replace("-", "").replace("°", "").isdigit():
            # Numbers
            translated.append(w_lower)
        elif w_lower in ("a", "an", "the"):
            # Skip articles in Persian
            continue
        elif w_lower in ("and",):
            translated.append("و")
        elif w_lower in ("or",):
            translated.append("یا")
        elif w_lower in ("while", "as"):
            translated.append("در حالی که")
        elif w_lower in ("then",):
            translated.append("سپس")
        elif w_lower in ("also",):
            translated.append("نیز")
        elif w_lower in ("if",):
            translated.append("اگر")
        elif w_lower in ("but",):
            translated.append("اما")
        elif w_lower in ("so",):
            translated.append("بنابراین")
        elif w_lower in ("until",):
            translated.append("تا")
        elif w_lower in ("before",):
            translated.append("قبل از")
        elif w_lower in ("after",):
            translated.append("بعد از")
        elif w_lower in ("that", "which", "who"):
            translated.append("که")
        elif w_lower in ("this", "these"):
            translated.append("این")
        elif w_lower in ("your", "the"):
            continue  # skip possessives/articles
        else:
            # Keep unknown words as-is (likely English)
            translated.append(w)

    return " ".join(translated)


def translate_instructions(en_instructions: dict) -> dict:
    """Translate the instructions object, adding 'fa' key."""
    en_text = en_instructions.get("en", "")
    if not en_text:
        return en_instructions.copy()

    sentences = re.split(r"(?<=[.!])\s+", en_text)
    fa_sentences = []
    for sent in sentences:
        if sent.strip():
            fa_sentences.append(translate_instruction_sentence(sent))

    result = en_instructions.copy()
    result["fa"] = " ".join(fa_sentences)
    return result


def translate_instruction_steps(en_steps: dict) -> dict:
    """Translate instruction_steps, adding 'fa' key."""
    en_list = en_steps.get("en", [])
    fa_list = [translate_instruction_sentence(s) for s in en_list]
    result = en_steps.copy()
    result["fa"] = fa_list
    return result


def translate_secondary_muscles(muscles: list) -> list:
    """Translate list of muscle names."""
    return [muscle_group_fa.get(m.lower(), m) for m in muscles]


# ── 5. Main processing loop ──────────────────────────────────────────────

updated = 0
errors = 0

for ex in exercises:
    try:
        # name → name_fa
        ex["name_fa"] = translate_exercise_name(ex["name"])

        # instructions.en → instructions.fa
        ex["instructions"] = translate_instructions(ex["instructions"])

        # instruction_steps.en → instruction_steps.fa
        ex["instruction_steps"] = translate_instruction_steps(ex["instruction_steps"])

        # category → category_fa
        cat = ex.get("category", "")
        if cat in category_fa:
            ex["category_fa"] = category_fa[cat]

        # body_part → body_part_fa
        bp = ex.get("body_part", "")
        if bp in body_part_fa:
            ex["body_part_fa"] = body_part_fa[bp]

        # equipment → equipment_fa
        eq = ex.get("equipment", "")
        if eq in equipment_fa:
            ex["equipment_fa"] = equipment_fa[eq]

        # muscle_group → muscle_group_fa
        mg = ex.get("muscle_group", "")
        if mg in muscle_group_fa:
            ex["muscle_group_fa"] = muscle_group_fa[mg]

        # secondary_muscles → translated
        ex["secondary_muscles_fa"] = translate_secondary_muscles(ex.get("secondary_muscles", []))

        # target → target_fa
        tg = ex.get("target", "")
        if tg in target_fa:
            ex["target_fa"] = target_fa[tg]

        updated += 1
    except Exception as e:
        errors += 1
        print(f"Error on {ex.get('id', '?')}: {e}", file=sys.stderr)

print(f"Updated: {updated}/{len(exercises)}", file=sys.stderr)
if errors:
    print(f"Errors: {errors}", file=sys.stderr)

# Write output
with open("exercises.json", "w", encoding="utf-8") as f:
    json.dump(exercises, f, ensure_ascii=False, indent=2)

print("Done! Wrote to exercises.json", file=sys.stderr)
