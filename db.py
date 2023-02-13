import sqlite3


class DataBase:
    """Класс работы с базой данных проекта. Объект класса привязывается к
    идентификатору каждого пользователя.
    """

    def __init__(self, user_id=None):
        self.connection = sqlite3.connect('db/cogorta.sqlite')
        self.cursor = self.connection.cursor()
        self.user_id = user_id

    def create_database(self):
        """Инициализирует базу данных.
        """
        with self.connection:
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                name TEXT,
                city TEXT,
                country TEXT,
                timezone TEXT,
                utc_offset INTEGER
            );
            ''')
        return True

    def create_user(self, name, city, country, timezone, utc_offset):
        """Сохраняет информацию о пользователе.
        """
        with self.connection:
            self.cursor.execute('''
                INSERT INTO users (
                    user_id, name, city, country, timezone, utc_offset)
                VALUES(?, ?, ?, ?, ?, ?);
                ''', (self.user_id, name, city, country, timezone, utc_offset))

    def load_user(self):
        """Загружает информацию о сохраненном пользователе.
        """
        with self.connection:
            self.cursor.execute('''
                SELECT name, city, country, timezone, utc_offset
                FROM users
                WHERE user_id = ?;
                ''', (self.user_id,))
        return self.cursor.fetchone()

    def get_local_users(self, city):
        """Получает список земляков пользователя из того же города.
        """
        with self.connection:
            self.cursor.execute('''
                SELECT user_id
                FROM users
                WHERE city = ?;
                ''', (city,))
        return [user[0] for user in self.cursor.fetchall()]

    def get_local_users_foreign(self, country):
        """Получает список земляков пользователя из той же страны.
        """
        with self.connection:
            self.cursor.execute('''
                SELECT user_id
                FROM users
                WHERE country = ?;
                ''', (country,))
        return [user[0] for user in self.cursor.fetchall()]

    def check_user_exist(self):
        """Проверяет существование записи о пользователе с заданным ID в БД.
        """
        with self.connection:
            self.cursor.execute('''
            SELECT EXISTS
            (SELECT * FROM users
            WHERE user_id = ?);
            ''', (self.user_id,))
        return self.cursor.fetchone()[0]

    def get_locations_ru(self):
        """Представляет информацию о городе проживания всех пользователей из
        России.
        """
        with self.connection:
            self.cursor.execute('''
            SELECT city, COUNT(user_id) AS people
            FROM users
            WHERE country = 'Россия'
            GROUP BY city
            ORDER BY people DESC;
            ''')
        return self.cursor.fetchall()

    def get_locations_ino(self):
        """Представляет информацию о стране проживания всех пользователей за
        пределами России.
        """
        with self.connection:
            self.cursor.execute('''
            SELECT country, COUNT(user_id) AS people
            FROM users
            WHERE country <> 'Россия'
            GROUP BY country
            ORDER BY people DESC;
            ''')
        return self.cursor.fetchall()

    def get_timezones(self):
        """Представляет информацию о часовых поясах всех пользователей.
        """
        with self.connection:
            self.cursor.execute('''
            SELECT timezone, utc_offset, COUNT(user_id) AS people
            FROM users
            GROUP BY timezone
            ORDER BY people DESC;
            ''')
        return self.cursor.fetchall()

    def close(self):
        """Закрывает соединение с базой данных.
        """
        self.connection.close()
