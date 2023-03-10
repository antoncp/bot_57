import datetime as dt

import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder


def check_city(city):
    """Проверяет существование введенного пользователем города. Если город
    существует, возвращает страну, полное название города, часовой пояс и
    часовое смещение относительно UTC.
    """
    geolocator = Nominatim(user_agent="test_bot")
    geo_location = geolocator.geocode(city)
    if geo_location is None:
        return (False, False, False, False)
    latitude = geo_location.latitude
    longitude = geo_location.longitude
    country, place, timezone = find_location(latitude, longitude)
    utc_offset = time_offset(timezone)
    return country, place, timezone, utc_offset


def coordinates_to_city(latitude, longitude):
    """Трансформирует координаты, полученные по геолокации в название города.
    Возвращает страну, полное название города, часовой пояс и
    часовое смещение относительно UTC.
    """
    country, place, timezone = find_location(latitude, longitude)
    utc_offset = time_offset(timezone)
    return country, place, timezone, utc_offset


def time_offset(timezone):
    """Высчитывает часовое смещение относительно UTC для представленного
    часового пояса.
    """
    utc_offset = dt.datetime.now(pytz.timezone(timezone)).strftime('%z')
    return int(utc_offset[:-2])


def local_time(timezone, time=None):
    """Конвертирует время UTC в локальное время пользователя с учетом его
    часового пояса.
    """
    if not time:
        time = dt.datetime.utcnow()
    else:
        time = dt.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    local = time.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(timezone))
    return local.strftime('%H-%M')


def timer_alert(time):
    """Проверяет запущенные таймеры на превышение времени."""
    time_now = dt.datetime.utcnow()
    time_start = dt.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    time_dif = time_now - time_start
    if time_dif.total_seconds() > 28800:
        return 'close'
    if time_dif.total_seconds() > 60 and time_dif.total_seconds() % 3600 <= 59:
        return 'alert'
    return False


def find_location(latitude, longitude):
    """Предоставляет страну, город, часовой пояс для заданных координат."""
    geolocator = Nominatim(user_agent="test_bot")
    political_location = geolocator.reverse(
        f"{latitude},{longitude}", language='ru'
    )
    address = political_location.raw['address']
    country = address['country']
    if address.get('city') is not None:
        place = address.get('city')
    elif address.get('town') is not None:
        place = address.get('town')
    elif address.get('village') is not None:
        place = address.get('village')
    else:
        place = "Ближайшее место не определено"
    obj = TimezoneFinder()
    timezone = obj.timezone_at(lng=longitude, lat=latitude)
    return country, place, timezone


def map_users(list_of_locations):
    """Генерирует географическую карту расположения пользователей бота
    через API Яндекс.Карт. Возвращает ссылку на карту, в которой каждая
    геометка сопровождается числом проживающих там пользователей. Всего
    возвращает две карты - мировую и европейской части РФ.
    """
    url = 'https://static-maps.yandex.ru/1.x/?lang=ru_RU&l=map&pt='
    url_eu = (
        'https://static-maps.yandex.ru/1.x/?lang=ru_RU&l=map'
        '&bbox=27.9,44.5~62.8,62.5&&pt='
    )
    for city, num in list_of_locations:
        geolocator = Nominatim(user_agent="test_map_bot")
        geo_location = geolocator.geocode(city)
        latitude = geo_location.latitude
        longitude = geo_location.longitude
        url += f'{longitude:.5f},{latitude:.5f},pm2rdl{num}~'
        if 45 < latitude < 62 and 28 < longitude < 62:
            url_eu += f'{longitude:.5f},{latitude:.5f},pm2rdl{num}~'
    return url[:-1], url_eu[:-1]
