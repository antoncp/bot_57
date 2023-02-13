from db import DataBase


class User:
    """Класс Пользователь позволяет создавать объекты, ассоциированные с
    каждым клиентом бота. Содержит в себе информацию о пользователе: имя,
    город, страну, название и смещение часового пояса. Кроме того, может
    хранить данные с идентификаторами земляков пользователя, а также флаг
    о том, что данные пользователя, записаны в БД.
    """
    list_of_users = set()

    def __init__(self, user_id, locals=None, name=None, city=None,
                 country=None, timezone=None, utc_offset=None, record=False):
        self.id = user_id
        self.locals = locals
        self.name = name
        self.city = city
        self.country = country
        self.timezone = timezone
        self.utc_offset = utc_offset
        self.record = record
        User.list_of_users.add(self)

    def __str__(self):
        return self.id

    def __repr__(self):
        return str(self.id)

    def load_from_db(self):
        """Загружает информацию о сохраненном пользователе из БД.
        """
        db = DataBase(self.id)
        (self.name, self.city, self.country,
         self.timezone, self.utc_offset) = db.load_user()
        self.record = True
        db.close()

    def save_user(self):
        """Сохраняет информацию о пользователе в БД.
        """
        db = DataBase(self.id)
        if not db.check_user_exist() and self.timezone:
            db.create_user(self.name, self.city,
                           self.country, self.timezone, self.utc_offset)
            db.close()
            self.record = True
            return True
        db.close()
        return False

    def get_locals(self):
        """Получает список земляков пользователя, проживающих в том же городе
        в случае с Россией или той же стране.
        """
        db = DataBase(self.id)
        if self.country == 'Россия':
            locals = db.get_local_users(self.city)
        else:
            locals = db.get_local_users_foreign(self.country)
        if self.id in locals:
            locals.remove(self.id)
        self.locals = locals
        db.close()
        return self.locals


def activate_user(user_id):
    """Возвращает объект класса Пользователь. Если соответствующего объекта
    нет в памяти, создает его и загружает связанные данные из БД.
    """
    user = next(
        (obj for obj in globals()['User'].list_of_users if obj.id == user_id),
        None)
    if not user:
        user = User(user_id)
        db = DataBase(user_id)
        if db.check_user_exist():
            user.load_from_db()
        db.close()
    return user
