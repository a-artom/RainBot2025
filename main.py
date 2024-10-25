import telebot
import requests
import schedule
import datetime

from threading import Thread
from time import sleep
from fake_useragent import UserAgent

import messages as msgs
from config import *
from datasave import *

if __name__ == '__main__':
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

    ua = UserAgent()

    time_btns = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for btn in TIMES.keys():
        time_btns.add(btn)
    hideBoard = telebot.types.ReplyKeyboardRemove()

    users = load_data("users.txt")


def schedule_checker():
    while True:
        try:
            schedule.run_pending()
            sleep(30)
        except Exception as e:
            print(e)


def check_schedules():
    now = datetime.datetime.now()

    if schedule.get_jobs():
        for job in schedule.get_jobs():
            schedule.cancel_job(job)

    for user in users.keys():
        send_time = datetime.datetime.strptime(users[user][1], TIME_FORMAT)

        if now >= send_time:
            users[user][1] = now.strftime(TIME_FORMAT)
            send_weather(user, users[user][0])
        else:
            schedule.every().day.at(send_time.strftime("%H:%M")).do(send_weather, user, users[user][0])


@bot.message_handler(commands=["start"])
def send_welcome(message):
    msg = bot.send_message(message.chat.id, msgs.START.format(user=message.from_user.first_name))
    bot.register_next_step_handler(msg, validate_city)


@bot.message_handler(commands=["stop"])
def send_welcome(message):
    del users[str(message.chat.id)]
    save_data(users, "users.txt")
    bot.send_message(message.chat.id, msgs.STOP)


def validate_city(message):
    weather_data = requests.get(API_REQUEST, headers={"User-Agent": ua.random},
                                params={"q": message.text, "appid": OPENWEATHER_API_KEY}).json()
    if weather_data["cod"] == "404":
        msg = bot.send_message(message.chat.id, msgs.CITY_IDK)
        bot.register_next_step_handler(msg, validate_city)
    elif weather_data["cod"] == 200:
        msg = bot.send_message(message.chat.id, msgs.CITY_FOUNDED, reply_markup=time_btns)
        bot.register_next_step_handler(msg, ask_time, city=message.text)
    else:
        msg = bot.send_message(message.chat.id, msgs.ERROR)
        bot.send_message(ADMIN_ID, f"User: {message.chat.id}, @{message.from_user.username}\n"
                                   f"Weather error:{weather_data}")


def ask_time(message, city):
    if message.text in TIMES.keys():
        msg = bot.send_message(message.chat.id, msgs.SUCCESS_TIME, reply_markup=hideBoard)
        now = datetime.datetime.now()
        users[str(message.chat.id)] = [city, now.strftime(TIME_FORMAT), TIMES[message.text]]
        save_data(users, "users.txt")
        send_weather(message.chat.id, city)
    else:
        msg = bot.send_message(message.chat.id, msgs.TIME_IDK)
        bot.register_next_step_handler(msg, ask_time, city=city)


def time_work(chat_id):
    chat_id = str(chat_id)
    send_time = (datetime.datetime.strptime(users[chat_id][1], TIME_FORMAT) +
                 datetime.timedelta(minutes=int(users[chat_id][2])))
    users[chat_id][1] = send_time.strftime(TIME_FORMAT)
    save_data(users, "users.txt")
    schedule.every().day.at(send_time.strftime("%H:%M")).do(send_weather, chat_id, users[chat_id][0])


def send_weather(chat_id, city):
    if str(chat_id) in users.keys():
        weather_data = requests.get(API_REQUEST, headers={"User-Agent": ua.random},
                                    params={"q": city, "appid": OPENWEATHER_API_KEY,
                                            "lang": "ru", "units": "metric"}).json()

        temp = weather_data["main"]["temp"]
        desc = weather_data["weather"][0]["description"]
        humidity = weather_data["main"]["humidity"]
        pressure = weather_data["main"]["pressure"]
        speed = weather_data["wind"]["speed"]

        bot.send_message(chat_id, msgs.WEATHER_SEND.format(city=city, temp=temp, desc=desc, humidity=humidity,
                                                           pressure=pressure, speed=speed))

        time_work(chat_id)

    return schedule.CancelJob


if __name__ == '__main__':
    schedule_thread = Thread(target=schedule_checker)
    check_schedules()
    schedule_thread.start()

    bot.infinity_polling()
