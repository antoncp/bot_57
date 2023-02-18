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


def find_location(latitude, longitude):
    """Предоставляет страну, город, часовой пояс для заданных координат."""
    geolocator = Nominatim(user_agent="test_bot")
    political_location = geolocator.reverse(
        f"{latitude},{longitude}", language='ru')
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
    геометка сопровождается числом проживающих там пользователей.
    """
    url = 'https://static-maps.yandex.ru/1.x/?lang=ru_RU&l=map&pt='
    for city, num in list_of_locations:
        geolocator = Nominatim(user_agent="test_bot")
        geo_location = geolocator.geocode(city)
        latitude = geo_location.latitude
        longitude = geo_location.longitude
        url += f'{longitude:.5f},{latitude:.5f},pm2rdl{num}~'
    return url[:-1]
