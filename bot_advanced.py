
import telebot
from telebot import types
from datetime import datetime, timedelta
import json
import os
import threading
import time

# ---------- إعدادات ----------
TOKEN = '7948600884:AAGxX7SW6SSqT-UnprA0lLbBaMYrQVcE1ms'
bot = telebot.TeleBot(TOKEN)
DATA_FILE = 'schedules.json'

user_states = {}
user_schedules = {}

DAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
DAY_MAP = {
    'الأحد': 6, 'الاثنين': 0, 'الثلاثاء': 1, 'الأربعاء': 2, 'الخميس': 3
}
TIMES = [f"{hour:02d}:00" for hour in range(8, 18)] + ['أخرى']

STATE_DAY = 'day'
STATE_SUBJECT = 'subject'
STATE_TIME = 'time'
STATE_CUSTOM_TIME = 'custom_time'
STATE_CONFIRM = 'confirm'
STATE_DELETE = 'delete'

# ---------- حفظ واسترجاع ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_schedules, f, ensure_ascii=False, indent=2)

user_schedules = load_data()

# ---------- تنبيهات تلقائية ----------
def send_reminders():
    while True:
        now = datetime.now()
        for user_id, entries in user_schedules.items():
            for entry in entries:
                day = entry['day']
                time_str = entry['time']
                dt = datetime.strptime(time_str, '%H:%M')
                target = dt.replace(
                    year=now.year, month=now.month, day=now.day,
                    minute=dt.minute - 10 if dt.minute >= 10 else 0
                )
                if now.weekday() == DAY_MAP[day] and now.strftime('%H:%M') == target.strftime('%H:%M'):
                    bot.send_message(int(user_id), f"🔔 تذكير: عندك حصة {entry['subject']} الساعة {entry['time']}")
        time.sleep(60)

threading.Thread(target=send_reminders, daemon=True).start()

# ---------- واجهة الاستخدام ----------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    user_states[user_id] = {'state': STATE_DAY, 'data': {}}
    if user_id not in user_schedules:
        user_schedules[user_id] = []
    bot.send_message(user_id, """👋 مرحباً بك في بوت "منظمي"!

📚 أنا هنا علشان أساعدك ترتب جدولك الدراسي، أذكّرك بحصصك، وأخليك تركز على أهدافك!

🛠 المزايا:
- إضافة حصص وتنظيم الجدول.
- تنبيهات تلقائية قبل الحصة.
- عرض مرتب حسب الأيام والأوقات.
- فهم أوامر بلغة طبيعية مثل: "ضيف رياضيات الاثنين 9:30".
- حذف وتعديل الحصص بسهولة.

اكتب /start للبدء أو جرب ترسل لي أمر بلغة عادية!
""")
    send_day_options(user_id)

@bot.message_handler(commands=['جدولي'])
def show_schedule_cmd(message):
    send_schedule(str(message.chat.id))

@bot.message_handler(commands=['حذف'])
def delete_entry_cmd(message):
    user_id = str(message.chat.id)
    schedule = user_schedules.get(user_id, [])
    if not schedule:
        bot.send_message(user_id, "📭 جدولك فارغ، ما فيه شي تحذفه.")
        return
    user_states[user_id] = {'state': STATE_DELETE}
    send_delete_options(user_id)

def send_day_options(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for day in DAYS:
        markup.add(day)
    bot.send_message(user_id, "📅 اختر اليوم:", reply_markup=markup)

def send_time_options(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for t in TIMES:
        markup.add(t)
    bot.send_message(user_id, "⏰ اختر وقت الحصة:", reply_markup=markup)

def send_delete_options(user_id):
    schedule = user_schedules.get(user_id, [])
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for idx, entry in enumerate(schedule):
        markup.add(f"{idx+1}")
    markup.add("إلغاء")
    bot.send_message(user_id, "📋 اختر رقم الحصة اللي تبي تحذفها:", reply_markup=markup)

def get_confirm_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("➕ إضافة حصة أخرى", "✅ إنهاء الجدول", "🗑️ حذف حصة")
    return markup

def valid_time_format(t):
    try:
        datetime.strptime(t, '%H:%M')
        return True
    except:
        return False

def is_time_in_range(t):
    try:
        time_obj = datetime.strptime(t, '%H:%M').time()
        return datetime.strptime('08:00', '%H:%M').time() <= time_obj <= datetime.strptime('17:00', '%H:%M').time()
    except:
        return False

def save_session(user_id):
    temp = user_states[user_id]['data']
    if user_id not in user_schedules:
        user_schedules[user_id] = []
    user_schedules[user_id].append(temp.copy())
    save_data()
    user_states[user_id]['data'] = {}
    user_states[user_id]['state'] = STATE_CONFIRM

    markup = get_confirm_markup()
    msg = f"✅ تم إضافة: {temp['day']} - {temp['subject']} ⏰ {temp['time']}"
    bot.send_message(user_id, msg, reply_markup=markup)

def send_schedule(user_id):
    schedule = sorted(user_schedules.get(user_id, []), key=lambda x: (DAY_MAP[x['day']], x['time']))
    if not schedule:
        bot.send_message(user_id, "📭 جدولك فارغ.")
        return
    text = "📚 جدولك الدراسي:

"
    for idx, s in enumerate(schedule):
        text += f"{idx+1}. {s['day']} - {s['subject']} ⏰ {s['time']}
"
    bot.send_message(user_id, text)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = str(message.chat.id)
    text = message.text.strip()

    if user_id not in user_states:
        if any(day in text for day in DAYS) and ':' in text:
            try:
                parts = text.split()
                subject = parts[2]
                day = parts[3]
                time = parts[4]
                if day in DAYS and valid_time_format(time):
                    user_schedules.setdefault(user_id, []).append({
                        'day': day, 'subject': subject, 'time': time
                    })
                    save_data()
                    bot.send_message(user_id, f"✅ أضفت لك {subject} يوم {day} الساعة {time}")
                    return
            except:
                pass
        bot.send_message(user_id, "اكتب /start للبدء.")
        return

    state = user_states[user_id].get('state')
    temp = user_states[user_id].get('data', {})

    if state == STATE_DAY:
        if text not in DAYS:
            send_day_options(user_id)
            return
        temp['day'] = text
        user_states[user_id]['state'] = STATE_SUBJECT
        user_states[user_id]['data'] = temp
        bot.send_message(user_id, "✏️ اكتب اسم الحصة (مثلاً: رياضيات، لغة إنجليزية، إلخ):")

    elif state == STATE_SUBJECT:
        if not text:
            bot.send_message(user_id, "❗ اكتب اسم الحصة، لا تتركها فارغة.")
            return
        temp['subject'] = text
        user_states[user_id]['state'] = STATE_TIME
        user_states[user_id]['data'] = temp
        send_time_options(user_id)

    elif state == STATE_TIME:
        if text == 'أخرى':
            user_states[user_id]['state'] = STATE_CUSTOM_TIME
            bot.send_message(user_id, "⌨️ اكتب وقت الحصة (مثلاً: 08:30):")
        elif valid_time_format(text) and is_time_in_range(text):
            temp['time'] = text
            user_states[user_id]['data'] = temp
            save_session(user_id)
        else:
            send_time_options(user_id)

    elif state == STATE_CUSTOM_TIME:
        if valid_time_format(text) and is_time_in_range(text):
            temp['time'] = text
            user_states[user_id]['data'] = temp
            save_session(user_id)
        else:
            bot.send_message(user_id, "❗ الصيغة غير صحيحة أو الوقت خارج النطاق 08:00 - 17:00. حاول مثلاً: 08:30")

    elif state == STATE_CONFIRM:
        if text == "➕ إضافة حصة أخرى":
            user_states[user_id] = {'state': STATE_DAY, 'data': {}}
            send_day_options(user_id)
        elif text == "✅ إنهاء الجدول":
            send_schedule(user_id)
            user_states.pop(user_id)
        elif text == "🗑️ حذف حصة":
            if not user_schedules.get(user_id, []):
                bot.send_message(user_id, "📭 جدولك فارغ، ما فيه شي تحذفه.")
                return
            user_states[user_id] = {'state': STATE_DELETE}
            send_delete_options(user_id)
        else:
            bot.send_message(user_id, "اختر من الأزرار:", reply_markup=get_confirm_markup())

    elif state == STATE_DELETE:
        if text == "إلغاء":
            bot.send_message(user_id, "تم إلغاء الحذف.", reply_markup=types.ReplyKeyboardRemove())
            user_states[user_id] = {'state': STATE_DAY, 'data': {}}
            send_day_options(user_id)
            return

        schedule = user_schedules.get(user_id, [])
        if text.isdigit():
            index = int(text) - 1
            if 0 <= index < len(schedule):
                removed = schedule.pop(index)
                save_data()
                bot.send_message(user_id, f"🗑️ حُذفت الحصة: {removed['day']} - {removed['subject']} ⏰ {removed['time']}", reply_markup=types.ReplyKeyboardRemove())
                user_states[user_id] = {'state': STATE_DAY, 'data': {}}
                send_day_options(user_id)
            else:
                bot.send_message(user_id, "❗ رقم الحصة غير صحيح، حاول مرة ثانية.")
                send_delete_options(user_id)
        else:
            bot.send_message(user_id, "❗ اكتب رقم الحصة للحذف.")
            send_delete_options(user_id)

bot.infinity_polling()
