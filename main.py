import logging
import os
from threading import Timer

import telebot
from dotenv import load_dotenv
from telebot.types import (
    BotCommand,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import log
from db import DataBase
from geo import (
    check_city,
    coordinates_to_city,
    local_time,
    map_users,
    timer_alert,
)
from texts import REMARKS
from user import User, activate_user

load_dotenv()
TEL_TOKEN = os.environ.get('TEL_TOKEN')
bot = telebot.TeleBot(TEL_TOKEN)


# Установка команд меню бота
bot.set_my_commands(
    [
        BotCommand("/new", "Указать свои имя и город"),
        BotCommand("/message", "Написать всем землякам"),
        BotCommand("/locations", "Показать все города"),
        BotCommand("/timezones", "Часовые пояса"),
        BotCommand("/timer", "Таймер учебы"),
    ]
)


# Реакции на глобальные команды бота
@bot.message_handler(commands=['start', 'help'])
def start(message):
    """Выводит стартовое сообщение бота."""
    bot.send_message(message.chat.id, REMARKS['intro'], parse_mode='Markdown')


@bot.message_handler(commands=['new'])
def new(message):
    """Запускает процесс регистрации нового пользователя."""
    user = activate_user(message.chat.id)
    if user.record:
        bot.send_document(
            message.chat.id,
            (
                'CgACAgIAAxkDAAMMY-oXBpKk7qbSEbcUFo1VgM_N'
                'ZwADniIAAueiUUsNLalUHu6Nly4E'
            ),
            caption=f'{user.name} из {user.city}, {user.country}, вы уже есть'
            ' в базе. Данные нельзя поменять.',
        )
        return

    provide_name = InlineKeyboardMarkup()
    provide_name.add(
        InlineKeyboardButton(text='Указать свое имя', callback_data='name')
    )
    bot.send_message(
        message.chat.id,
        REMARKS['name'],
        reply_markup=provide_name,
        parse_mode='Markdown',
    )


@bot.message_handler(commands=['message'])
def message(message):
    """Проверяет наличие земляков и позволяет написать им сообщение
    после подтверждения.
    """
    user = activate_user(message.chat.id)
    if not user.record:
        answer = 'Сначала укажите ваш город. Город не определен.'
        bot.send_message(message.chat.id, answer)
        return

    locals = user.get_locals()
    if not locals:
        answer = (
            f'{user.name}, в вашем городе пока зарегистрированы '
            'только вы. Ждем пополнения.'
        )
        bot.send_message(message.chat.id, answer)
        return

    num = len(locals)
    if user.country == 'Россия':
        answer = REMARKS['locals'].format(user.city, num)
    else:
        answer = REMARKS['locals_ino'].format(user.country, num)
    send_message = InlineKeyboardMarkup()
    send_message.add(
        InlineKeyboardButton(
            text='Написать им всем сообщение', callback_data='callall'
        )
    )
    bot.send_message(
        message.chat.id,
        answer,
        reply_markup=send_message,
        parse_mode='Markdown',
    )


@bot.message_handler(commands=['locations'])
def get_all_locations(message):
    """Выводит географию всех зарегистрированных пользователей бота."""
    db = DataBase(message.chat.id)
    ru = db.get_locations_ru()
    ino = db.get_locations_ino()
    db.close()
    num = sum([i[1] for i in ru]) + sum([i[1] for i in ino])
    header_ru = (
        '_География студентов когорты 57 в этом боте_ '
        f'_(всего {num} чел.)_\n'
        'Студенты из городов 🇷🇺\n'
        '*Город* *|*   *Кол-во человек*\n'
        '---------------------------------\n'
    )
    header_ino = (
        '\n---------------------------------\n'
        'Студенты из других стран\n'
        '*Страна* *|*   *Кол-во человек*\n'
        '---------------------------------\n'
    )
    ru_list = 'Пока никого нет'
    ino_list = 'Пока никого нет'
    if ru:
        ru_list = '\n'.join([f'*{city}*: `{people}`' for city, people in ru])
    if ino:
        ino_list = '\n'.join([f'*{cou}*: `{people}`' for cou, people in ino])
    answer = header_ru + ru_list + header_ino + ino_list
    bot.send_message(message.chat.id, answer, parse_mode='Markdown')
    if num != User.num_of_users:
        User.num_of_users = num
        map_url = map_users(ru + ino)
        User.map_url = map_url
    else:
        map_url = User.map_url
    bot.send_photo(message.chat.id, map_url, caption='Наши студенты на карте')
    logging.warning(log(message, 'Запрос карты пользователей'))


@bot.message_handler(commands=['timezones'])
def get_all_timezones(message):
    """Выводит часовые пояса всех зарегистрированных пользователей бота."""
    db = DataBase(message.chat.id)
    time = db.get_timezones()
    db.close()
    utc_shift = 3
    if time:
        utc_shift = sum([i[1] * i[2] for i in time]) / sum(
            [i[2] for i in time]
        )
    moscow_shift = utc_shift - 3
    header = (
        '_Часовые пояса студентов когорты 57 в этом боте_\n'
        f'Среднее смещение {utc_shift:.1f} час. относительно UTC '
        f'(Гринвич), {moscow_shift:.1f} час. - относительно Москвы.\n'
        '*Часовой пояс* *|*     *Кол-во человек*\n'
        '----------------------------------------\n'
    )
    timezone_stats = 'Пока никого нет'
    if time:
        timezone_stats = '\n'.join(
            [
                f'*{zone}* _(UTC +{utc} ч.)_: `{people}`'
                for zone, utc, people in time
            ]
        )
    answer = header + timezone_stats
    bot.send_message(message.chat.id, answer, parse_mode='Markdown')
    logging.warning(log(message, 'Запрос часовых поясов пользователей'))


@bot.message_handler(content_types=['location'])
def location(message):
    """Обрабатывает геолокацию пользователя в случае отправки."""
    if not message.location:
        return
    user = activate_user(message.chat.id)
    country, city, timezone, utc_offset = coordinates_to_city(
        message.location.latitude, message.location.longitude
    )
    user.city = city
    user.country = country
    user.timezone = timezone
    user.utc_offset = utc_offset
    bot.send_message(
        message.chat.id,
        'Геолокация проведена.',
        reply_markup=ReplyKeyboardRemove(),
    )
    submit_user(message)


@bot.message_handler(commands=['timer'])
def timer(message):
    """Позволяет выбрать текущий спринт для запуска таймера учета учебного
    времени и выводит статистику по записанному времени.
    """
    user = activate_user(message.chat.id)
    if not user.record:
        answer = 'Сначала зарегистрируйтесь. Ваш город не определен.'
        bot.send_message(message.chat.id, answer)
        return
    if user.timer:
        bot.send_message(message.chat.id, 'У вас уже запущен таймер.')
        return
    sprint_select = InlineKeyboardMarkup(row_width=2)
    sprint_select.add(
        *[
            InlineKeyboardButton(
                text=f'Спринт № {spr}', callback_data=f'sprint {spr}'
            )
            for spr in range(3, 17)
        ]
    )
    sprint_select.add(
        InlineKeyboardButton(text='Спрятать таймер', callback_data='no_timer')
    )
    answer = REMARKS['timers']
    db = DataBase(message.chat.id)
    all_sprints = db.all_sprints()
    db.close()
    header = (
        '_Время, затраченное вами на прохождение спринтов_\n'
        'Вы можете выбрать свой текущий спринт для учета времени ниже, '
        'среди предложенных кнопок.\n\n'
        '*Спринт*  *|*  *Затрачено времени*\n'
        '----------------------------------------\n'
    )
    if all_sprints:
        sprints = '\n'.join(
            [
                f'*Спринт №{spr}*:  `{total_time}`'
                for spr, total_time in all_sprints
            ]
        )
        answer = header + sprints
    bot.send_message(
        message.chat.id,
        answer,
        parse_mode='Markdown',
        reply_markup=sprint_select,
    )


# Реакции на срабатывание инлайн-клавиатур бота
@bot.callback_query_handler(func=lambda call: call.data == 'name')
def provide_name(call):
    """Обрабатывает заполнение имени пользователя."""
    message = 'Впишите свое имя в поле ответа.'
    reply = ForceReply(input_field_placeholder='Меня зовут...')
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, message, reply_markup=reply)


@bot.callback_query_handler(func=lambda call: call.data == 'geo')
def provide_geo(call):
    """Обрабатывает заполнение города пользователя."""
    message = 'Впишите свой город в поле для ответа.'
    reply = ForceReply(input_field_placeholder='Мой город...')
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, message, reply_markup=reply)


@bot.callback_query_handler(func=lambda call: call.data == 'location')
def provide_location(call):
    """Формирует кнопку отправки геолокации."""
    message = REMARKS['location']
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = KeyboardButton(
        text="Отправить местоположение", request_location=True
    )
    keyboard.add(button_geo)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(
        call.message.chat.id,
        message,
        reply_markup=keyboard,
        parse_mode='Markdown',
    )


@bot.callback_query_handler(func=lambda call: call.data == 'delete')
def delete(call):
    """Обрабатывает отмену сохранения информации в БД."""
    message = 'Операция не завершена. Попробуйте снова.'
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, message)


@bot.callback_query_handler(func=lambda call: call.data == 'save')
def save_user(call):
    """Обрабатывает сохранение информации о пользователе в БД."""
    user = activate_user(call.message.chat.id)
    if user.save_user():
        bot.send_document(
            call.message.chat.id,
            (
                'CgACAgIAAxkDAAMJY-oV_47ABn3ZrCYpRDqxoexf'
                '3WMAApwiAALnolFLCGfyQJZf5HAuBA'
            ),
            caption='Данные сохранены. Поздравляем!',
        )
        alert_all(user)
        logging.warning(log(message, 'Регистрация нового пользователя'))
    else:
        bot.send_message(call.message.chat.id, 'Ошибка записи')
    bot.delete_message(call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == 'callall')
def call_all(call):
    """Обрабатывает отправку сообщения всем землякам."""
    message = 'Впишите свое сообщение. Его увидят все ваши земляки в чате.'
    reply = ForceReply(input_field_placeholder='Сообщение...')
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, message, reply_markup=reply)


@bot.callback_query_handler(func=lambda call: call.data == 'answerall')
def answer_all(call):
    """Обрабатывает ответ на сообщение земляка."""
    message = 'Впишите свое сообщение. Его увидят все ваши земляки в чате.'
    reply = ForceReply(input_field_placeholder='Сообщение...')
    bot.send_message(call.message.chat.id, message, reply_markup=reply)
    bot.answer_callback_query(callback_query_id=call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('sprint'))
def show_timer(call):
    """Показывает клавиатуру с кнопкой таймера для выбранного спринта."""
    user = activate_user(call.message.chat.id)
    if user.timer:
        return
    sprint_num = call.data.split()[-1]
    timer = ReplyKeyboardMarkup(
        row_width=1, resize_keyboard=True, one_time_keyboard=True
    )
    timer.add(f"Запустить таймер: cпринт № {sprint_num}")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(
        call.message.chat.id,
        'Нажмите на кнопку таймера внизу, когда начнете учебу.',
        reply_markup=timer,
    )


@bot.callback_query_handler(func=lambda call: call.data == 'no_timer')
def hide_timer(call):
    """Прячет клавиатуру запуска таймера"""
    user = activate_user(call.message.chat.id)
    if user.timer:
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(
        call.message.chat.id,
        'Таймер спрятан. Для активации снова выберите спринт',
        reply_markup=ReplyKeyboardRemove(),
    )


# Вынесенные функции бота
def submit_user(message):
    """Подтверждает первичное сохранение информации о пользователе в БД."""
    user = activate_user(message.chat.id)
    save_user = InlineKeyboardMarkup()
    save_user.add(
        InlineKeyboardButton(
            text='Сохранить свои данные', callback_data='save'
        )
    )
    save_user.add(
        InlineKeyboardButton(text='Не сохранять', callback_data='delete')
    )
    bot.send_message(
        message.chat.id,
        REMARKS['submit'].format(user.name, user.city, user.country),
        reply_markup=save_user,
        parse_mode='Markdown',
    )


def send_all(message):
    """Отправляет сообщение всем землякам пользователя."""
    user = activate_user(message.chat.id)
    locals = user.get_locals()
    if not locals:
        bot.send_message(
            chat_id=message.chat.id,
            text='Упс, что-то пошло не так. Не вижу ваших земляков.',
        )
        return
    if user.country == 'Россия':
        place = user.city
    else:
        place = user.country
    send_message = InlineKeyboardMarkup()
    send_message.add(
        InlineKeyboardButton(
            text='Ответить всем в чате земляков', callback_data='answerall'
        )
    )
    for loc in locals:
        bot.send_message(
            chat_id=loc,
            text=f'_Ваш земляк_ *{user.name}* _пишет_:\n{message.text}',
            reply_markup=send_message,
            parse_mode='Markdown',
        )
    bot.send_message(
        chat_id=message.chat.id,
        text=(
            f'Сообщение отправлено. Получатели: *{len(locals)}* чел.\n'
            f'Локация: {place}'
        ),
        parse_mode='Markdown',
    )
    logging.warning(log(message, f'Написал землякам {place}: {message.text}'))


def alert_all(user):
    """Информирует о появлении нового земляка."""
    locals = user.get_locals()
    if not locals:
        return
    for loc in locals:
        bot.send_document(
            chat_id=loc,
            document=(
                'CgACAgIAAxkDAAMJY-oV_47ABn3ZrCYpRDqxoexf'
                '3WMAApwiAALnolFLCGfyQJZf5HAuBA'
            ),
            caption=(
                'Среди ваших земляков пополнение. Приветствуйте, '
                f'*{user.name}*. Теперь вас *{len(locals)+1}* чел.'
            ),
            parse_mode='Markdown',
        )


def new_timer(message):
    """Инициирует запись о времени старта нового таймера учебы в БД."""
    user = activate_user(message.chat.id)
    if user.timer:
        return
    try:
        sprint = int(message.text.split()[-1])
    except ValueError:
        return
    if not 0 < sprint < 17:
        return
    db = DataBase(message.chat.id)
    db.start_timer(sprint)
    db.close()
    time = local_time(user.timezone)
    user.timer = True
    answer = f'Таймер запущен в *{time}*'
    stop_timer = ReplyKeyboardMarkup(
        row_width=1, resize_keyboard=True, one_time_keyboard=True
    )
    stop_timer.add(f"Остановить таймер (запущен в {time})")
    bot.send_message(
        message.chat.id, answer, parse_mode='Markdown', reply_markup=stop_timer
    )


def end_timer(user_id, forcibly=False):
    """Останавливает запущенный таймер, записывая время окончания в БД."""
    user = activate_user(user_id)
    if not user.timer:
        bot.send_message(
            user_id,
            'У вас нет запущенных таймеров.',
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    db = DataBase(user_id)
    db.end_timer()
    id = db.last_timer()[0]
    sprint, start, duration = db.last_timer_duration(id)
    sprint_time = db.sprint_time(sprint)[0]
    db.close()
    user.timer = None
    start = local_time(user.timezone, start)
    answer = REMARKS['timer_stop'].format(start, duration, sprint, sprint_time)
    if forcibly:
        header = (
            '*Вы занимаетесь больше 8 часов. Так долго учиться нельзя.* '
            '*Ваш таймер принудительно остановлен.*\n\n'
        )
        answer = header + answer
    timer = ReplyKeyboardMarkup(
        row_width=1, resize_keyboard=True, one_time_keyboard=True
    )
    timer.add(f"Запустить таймер: cпринт № {sprint}")
    bot.send_message(
        user_id, answer, parse_mode='Markdown', reply_markup=timer
    )


def monitoring():
    """Раз в минуту проверяет БД на предмет запущенных таймеров. Если
    пользователь занимается больше часа - высылает предупреждение об отдыхе.
    Если больше 8 часов - принудительно закрывает таймер.
    """
    one_minute_monitor = Timer(60.0, monitoring)
    one_minute_monitor.start()
    db = DataBase()
    active_timers = db.check_all_active_timers()
    db.close()
    if active_timers:
        for user_id, start_time in active_timers:
            status = timer_alert(start_time)
            if not status:
                break
            if status == 'alert':
                user = activate_user(user_id)
                start = local_time(user.timezone, start_time)
                bot.send_message(
                    user_id,
                    REMARKS['timer_alert'].format(start),
                    parse_mode='Markdown',
                )
            if status == 'close':
                end_timer(user_id, forcibly=True)


# Реакции на текстовые сообщения боту
@bot.message_handler(content_types=["text"])
def handle_text(message):
    """Обрабатывает все текстовые сообщения боту, в том числе заполнение имени,
    города при регистрации, отправку сообщения землякам.
    """
    user = activate_user(message.chat.id)
    if not message.reply_to_message:
        if message.text.startswith('Запустить таймер: cпринт №'):
            new_timer(message)
        elif message.text.startswith('Остановить таймер'):
            end_timer(message.chat.id)
        else:
            bot.send_message(
                message.chat.id,
                'Не понимаю, что вы хотите сказать. Воспользуйтесь ↙ Menu.',
            )
        return
    operation = message.reply_to_message.text
    if operation.startswith('Впишите свое имя') and not user.record:
        user.name = message.text[:20].title()
        provide_geo = InlineKeyboardMarkup()
        provide_geo.add(
            InlineKeyboardButton(
                text='Указать свой город', callback_data='geo'
            )
        )
        provide_geo.add(
            InlineKeyboardButton(
                text='Поделиться геолокацией', callback_data='location'
            )
        )
        bot.send_message(
            message.chat.id,
            REMARKS['geo'].format(user.name),
            reply_markup=provide_geo,
            parse_mode='Markdown',
        )
    if operation.startswith('Впишите свой город') and not user.record:
        country, city, timezone, utc_offset = check_city(message.text)
        if city:
            user.city = city
            user.country = country
            user.timezone = timezone
            user.utc_offset = utc_offset
            submit_user(message)
        else:
            bot.send_message(
                message.chat.id,
                'Не получилось идентифицировать город, попробуйте снова.',
            )
    if operation.startswith('Впишите свое сообщение'):
        bot.delete_message(
            message.chat.id, message.reply_to_message.message_id
        )
        send_all(message)


# Загрузка бота, инициализация базы данных при старте
if __name__ == '__main__':
    db = DataBase()
    db.create_database()
    db.close()
    monitoring()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
