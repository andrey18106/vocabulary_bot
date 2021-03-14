# -*- coding: utf-8 -*-

# TODO: Add user restrictions according to API limits
# TODO: (new words per day, total vocabulary capacity, available number of quizzes, number of instant translations)

# ===== Default imports =====

from config import DEFAULT_LANG
from datetime import datetime
import logging
import os
import random
import sqlite3
import time

# ===== Local imports =====

from itertools import islice
from translation import google_translate, leo_translate


class DbManager:
    """Class for working with bot database"""

    conn = None  # Connection to SQLite3 database

    def __init__(self, path_to_db: str):
        self.path_to_db = path_to_db

    def create_connection(self):
        try:
            self.conn = sqlite3.connect(self.path_to_db)
            if not self._database_created():
                self._init_database()
            logging.getLogger(type(self).__name__).info(
                f' SQLite {sqlite3.version} database successfully loaded '
                f'[size: {round(os.path.getsize(self.path_to_db) / 1000)} KB]')
            # self.__translate_stock_vocabulary(pack_size=980, offset=74)
            # self.__transcribe_stock_vocabulary(pack_size=1000, offset=2000)
        except sqlite3.Error as error:
            logging.getLogger(type(self).__name__).error(f' SQLite3 Connection Error ({error})')

    def close_connection(self):
        try:
            self.conn.close()
            logging.getLogger(type(self).__name__).info(f"Database connection successfully closed")
        except sqlite3.Error as error:
            logging.getLogger(type(self).__name__).error(f"Shutdown error [{error}]")

    def _database_created(self) -> bool:
        tables = ['users', 'words', 'metrics', 'analytics_log', 'permissions', 'admins', 'achievements',
                  'stock_vocabulary']
        query = '''SELECT name FROM sqlite_master WHERE type='table' AND name=?;'''
        result = True
        for table_name in tables:
            result &= len(self._execute_query(query, table_name).fetchall()) > 0
        return result

    def _init_database(self) -> None:
        users_table = '''CREATE TABLE users (
                            user_id INT PRIMARY KEY NOT NULL, 
                            user_nickname STRING, 
                            user_firstname STRING, 
                            user_lastname STRING, 
                            lang TEXT,
                            date_added DATETIME,
                            referrals INT DEFAULT (0),
                            referrer INT,
                            mailings INT DEFAULT (2) 
                        );'''
        words_table = '''CREATE TABLE words (
                        word_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        user_id INTEGER REFERENCES users (user_id) NOT NULL,
                        word_string TEXT NOT NULL,
                        word_translation TEXT,
                        date_added DATETIME NOT NULL,
                        from_lang TEXT,
                        to_lang TEXT
                    );'''
        metrics_table = '''CREATE TABLE metrics (
                            metric_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                            metric_name TEXT NOT NULL
                        );'''
        analytics_log_table = '''CREATE TABLE analytics_log (
                                    log_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                    metric INT NOT NULL REFERENCES metrics (metric_id), 
                                    count INT NOT NULL DEFAULT (1), user_id INT NOT NULL
                                );'''
        permissions_table = '''CREATE TABLE permissions (
                                permission_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                permission_name TEXT NOT NULL
                            );'''
        admins_table = '''CREATE TABLE admins (
                                admin_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                user_id INT NOT NULL, 
                                permission_level INTEGER NOT NULL REFERENCES permissions (permission_id)
                            );'''
        achievements_table = '''CREATE TABLE achievements (
                                achievement_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                achievement_name TEXT NOT NULL,
                                achievement_points INT NOT NULL,
                                achievement_threshold INT NOT NULL
                            );'''

        stock_vocabulary_table = '''CREATE TABLE stock_vocabulary (
                                    word_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                    word_string TEXT NOT NULL,
                                    word_translation TEXT,
                                    word_transcription TEXT,
                                    date_added DATETIME NOT NULL
                                );'''
        try:
            self.conn.execute(users_table)
            self.conn.execute(words_table)
            self.conn.execute(metrics_table)
            self.conn.execute(analytics_log_table)
            self.conn.execute(permissions_table)
            self.conn.execute(admins_table)
            self.conn.execute(achievements_table)
            self.conn.execute(stock_vocabulary_table)
            self.conn.commit()
            logging.getLogger(type(self).__name__).info('Database structure successfully created')
        except sqlite3.Error as error:
            logging.getLogger(type(self).__name__).error(f'Error while creating database.\n{error}')

    def _execute_query(self, query, *args) -> sqlite3.Cursor:
        try:
            return self.conn.execute(query, args)
        except sqlite3.Error as error:
            logging.getLogger(type(self).__name__).error(f' SQLite3 Query Execution Error ({error})\n {query}, {args}')

    def is_user_exists(self, user_id: int) -> bool:
        query = 'SELECT * FROM users WHERE user_id=?'
        return len(self._execute_query(query, user_id).fetchall()) > 0

    def add_user(self, user_id: int, user_nickname: str, user_firstname: str, user_lastname: str) -> None:
        query = '''INSERT INTO users (user_id, user_nickname, user_firstname, user_lastname, date_added) 
                   VALUES(?, ?, ?, ?, ?)'''
        self._execute_query(query, user_id, user_nickname, user_firstname, user_lastname, datetime.now().date())
        self.conn.commit()

    def get_user_lang(self, user_id: int) -> str:
        query = 'SELECT lang FROM users WHERE user_id=?'
        result = self._execute_query(query, user_id).fetchall()
        return str(result[0][0]) if len(result) > 0 else DEFAULT_LANG

    def set_user_lang(self, user_id: int, user_lang: str) -> None:
        query = 'UPDATE users SET lang=? WHERE user_id=?'
        self._execute_query(query, user_lang, user_id)
        self.conn.commit()

    def get_user_mailings(self, user_id: int) -> bool:
        query = 'SELECT mailings FROM users WHERE user_id=?'
        return bool(self._execute_query(query, user_id).fetchall()[0])

    def set_user_mailings(self, user_id: int, value: int):
        query = 'UPDATE users SET mailings=? WHERE user_id=?'
        self._execute_query(query, value, user_id)
        self.conn.commit()

    def add_metric(self, metric_name):
        query = 'INSERT INTO metrics (metric_name) VALUES (?)'
        self._execute_query(query, metric_name)
        self.conn.commit()

    def metric_exists(self, metric_id: int) -> bool:
        query = 'SELECT metric_id FROM metrics WHERE metric_id=?'
        return len(self._execute_query(query, metric_id).fetchall()) > 0

    def metric_name_exists(self, metric_name: str) -> bool:
        query = 'SELECT metric_id FROM metrics WHERE metric_name=?'
        return len(self._execute_query(query, metric_name).fetchall()) > 0

    def get_metric_id(self, metric_name: str) -> int:
        if self.metric_name_exists(metric_name):
            query = 'SELECT metric_id FROM metrics WHERE metric_name=?'
            return self._execute_query(query, metric_name).fetchall()[0][0]
        else:
            self.add_metric(metric_name)
            return self.get_metric_id(metric_name)

    def analytics_log_exists(self, user_id: int, metric_id: int) -> bool:
        return len(self._execute_query("SELECT user_id FROM analytics_log WHERE user_id=? AND metric=?",
                                       user_id, metric_id).fetchall()) > 0

    def log_default_metric(self, handler_name: str, user_id: int, metric_id: int) -> None:
        if not self.metric_exists(metric_id):
            self.add_metric(handler_name)
        if self.analytics_log_exists(user_id, metric_id):
            query = 'UPDATE analytics_log SET count=? WHERE user_id=? AND metric=?'
            count = self._execute_query('SELECT count FROM analytics_log WHERE user_id=? AND metric=?',
                                        user_id, metric_id).fetchall()[0][0]
            self._execute_query(query, count + 1, user_id, metric_id)
            self.conn.commit()
        else:
            query = 'INSERT INTO analytics_log (metric, user_id) VALUES (?, ?)'
            self._execute_query(query, metric_id, user_id)
            self.conn.commit()

    def log_callback_metric(self, callback_name: str, user_id: int, metric_id: int) -> None:
        if not self.metric_name_exists(callback_name):
            self.add_metric(callback_name)
        if self.analytics_log_exists(user_id, metric_id):
            query = 'UPDATE analytics_log SET count=? WHERE user_id=? AND metric=?'
            count = self._execute_query('SELECT count FROM analytics_log WHERE user_id=? AND metric=?',
                                        user_id, metric_id).fetchall()[0][0]
            self._execute_query(query, count + 1, user_id, metric_id)
            self.conn.commit()
        else:
            query = 'INSERT INTO analytics_log (metric, user_id) VALUES (?, ?)'
            self._execute_query(query, metric_id, user_id)
            self.conn.commit()

    def is_admin(self, user_id: int) -> bool:
        query = 'SELECT user_id FROM admins WHERE user_id=?'
        return len(self._execute_query(query, user_id).fetchall()) > 0

    def get_permissions_list(self) -> list:
        query = 'SELECT * FROM permissions'
        return self._execute_query(query).fetchall()[0]

    def get_user_dict(self, user_id: int) -> list:
        query = '''SELECT word_id, word_string, word_translation, from_lang, to_lang, date_added
                FROM words WHERE user_id=?'''
        user_dict = self._execute_query(query, user_id).fetchall()
        return user_dict

    def word_in_user_dict(self, word_id: int, user_id: int) -> bool:
        query = 'SELECT word_id FROM words WHERE word_id=? AND user_id=?'
        return len(self._execute_query(query, word_id, user_id).fetchall()) > 0

    def get_user_word(self, word_id: int, user_id: int) -> list:
        query = 'SELECT * FROM words WHERE word_id=? AND user_id=?'
        return self._execute_query(query, word_id, user_id).fetchall()[0]

    def get_admin_statistics(self) -> list:
        query = '''SELECT metric, SUM(count) AS metric_total, metrics.metric_name 
        FROM analytics_log INNER JOIN metrics ON metrics.metric_id = metric 
        GROUP BY metric ORDER BY metric_total DESC'''
        return self._execute_query(query).fetchall()

    def get_users_list(self) -> list:
        query = 'SELECT user_id FROM users'
        return self._execute_query(query).fetchall()

    def get_user_info(self, user_id: int) -> list:
        query = 'SELECT * FROM users WHERE user_id=?'
        return self._execute_query(query, user_id).fetchall()[0]

    def get_user_dict_capacity(self, user_id: int) -> int:
        query = 'SELECT * FROM words WHERE user_id=?'
        return len(self._execute_query(query, user_id).fetchall())

    def get_user_referral_count(self, user_id: int) -> int:
        query = 'SELECT referrals FROM users WHERE user_id=?'
        return self._execute_query(query, user_id).fetchall()[0][0]

    def update_referral_count(self, user_id: int):
        query = 'UPDATE users SET referrals=? WHERE user_id=?'
        self._execute_query(query, self.get_user_referral_count(user_id) + 1, user_id)
        self.conn.commit()

    def set_user_referrer(self, user_id: int, referrer_id: int):
        query = 'UPDATE users SET referrer=? WHERE user_id=?'
        self._execute_query(query, referrer_id, user_id)
        self.conn.commit()

    def get_user_referrer(self, user_id: int) -> int:
        query = 'SELECT referrer FROM users WHERE user_id=?'
        result = self._execute_query(query, user_id).fetchall()
        return result[0][0] if len(result) > 0 else None

    def add_user_word(self, word_string: str, word_translation: str, user_id: int, from_lang: str, to_lang: str):
        query = '''INSERT INTO words (user_id, word_string, word_translation, date_added, from_lang, to_lang)
                VALUES (?, ?, ?, ?, ?, ?)'''
        self._execute_query(query, user_id, word_string, word_translation, datetime.now().date(), from_lang, to_lang)
        self.conn.commit()

    def get_user_word_by_str(self, word_string: str, user_id: int) -> int:
        query = 'SELECT word_id FROM words WHERE user_id=? AND word_string=?'
        result = self._execute_query(query, user_id, word_string).fetchall()
        return result[0][0] if len(result) > 0 else None

    def delete_user_word(self, word_id: int, user_id: int):
        query = 'DELETE FROM words WHERE word_id=? AND user_id=?'
        self._execute_query(query, word_id, user_id)
        self.conn.commit()

    def word_is_users(self, word_id: int, user_id: int) -> bool:
        query = 'SELECT word_id FROM words WHERE word_id=? AND user_id=?'
        return len(self._execute_query(query, word_id, user_id).fetchall()) > 0

    def get_broadcast_users(self, mailings: int = 2) -> list:
        query = 'SELECT user_id FROM users WHERE mailings=?'
        result = self._execute_query(query, mailings).fetchall()
        return map(lambda item: item[0], result) if len(result) > 0 else []

    def _stat_pages(self, data: dict, size=10):
        it = iter(data)
        for i in range(0, len(data), size):
            yield {k: data[k] for k in islice(it, size)}

    def get_user_dict_last_word_date(self, user_id: int) -> datetime:
        query = 'SELECT date_added FROM words WHERE user_id=? ORDER BY date_added ASC'
        query_result = self._execute_query(query, user_id).fetchall()[0][0].split('-')
        result = datetime(int(query_result[0]), int(query_result[1]), int(query_result[2]))
        return result

    def get_user_dictionary_stats(self, user_id: int) -> dict:
        """TODO: Implement dictionary stats"""
        dates = dict()
        dates['years'] = dict()
        user_dict = self.get_user_dict(user_id)
        for word in user_dict:
            word_date = word[5].split('-')
            dt = datetime(int(word_date[0]), int(word_date[1]), int(word_date[2]))
            if not str(dt.year) in dates['years']:
                dates['years'][str(dt.year)] = dict()
                dates['years'][str(dt.year)]['months'] = dict()
                dates['years'][str(dt.year)]['total'] = 0
            if str(dt.year) in dates['years'] and not str(dt.month) in dates['years'][str(dt.year)]['months']:
                dates['years'][str(dt.year)]['months'][str(dt.month)] = dict()
                dates['years'][str(dt.year)]['months'][str(dt.month)]['total'] = 0
                dates['years'][str(dt.year)]['months'][str(dt.month)]['stats'] = dict()
            if str(dt.day) in dates['years'][str(dt.year)]['months'][str(dt.month)]['stats']:
                dates['years'][str(dt.year)]['months'][str(dt.month)]['stats'][str(dt.day)] += 1
                dates['years'][str(dt.year)]['months'][str(dt.month)]['total'] += 1
                dates['years'][str(dt.year)]['total'] += 1
            else:
                dates['years'][str(dt.year)]['months'][str(dt.month)]['stats'][str(dt.day)] = 1
                dates['years'][str(dt.year)]['months'][str(dt.month)]['total'] += 1
                dates['years'][str(dt.year)]['total'] += 1
        total_pages = 0
        total = 0
        for year in dates['years']:
            year_pages = 0
            for month in dates['years'][year]['months']:
                month_pages = list()
                for month_page_data in self._stat_pages(dates['years'][year]['months'][month]['stats'], 7):
                    month_pages.append(month_page_data)
                year_pages += len(month_pages)
                dates['years'][year]['months'][month]['stats'] = month_pages
                dates['years'][year]['months'][month]['pages'] = len(month_pages)
                total += dates['years'][year]['months'][month]['total']
            dates['years'][year]['pages'] = year_pages
            total_pages += year_pages
        dates['total_pages'] = total_pages
        dates['total'] = total
        return dates

    def _get_quiz_options(self, user_dict: list, word_string: str, word_translation: str, amount: int) -> list:
        result = [word_translation]
        while len(result) <= amount:
            index = random.randint(0, len(user_dict) - 1)
            if user_dict[index][1] != word_string \
                    and not user_dict[index][2] in result:
                result.append(user_dict[index][2].lower())
        return random.sample(result, len(result))

    def get_user_quiz_data(self, user_id: int, from_lang: str, to_lang: str) -> list:
        """TODO: Generating random quiz for different language pairs"""
        quiz_data = list()
        quiz_words = list()
        user_dict = self.get_user_dict(user_id)
        while len(quiz_data) < 3:
            index = random.randint(0, len(user_dict) - 1)
            if not user_dict[index][1] in quiz_words:
                quiz_words.append(user_dict[index][1])
                question_word = {
                    'word': user_dict[index][1],
                    'answer': user_dict[index][2],
                    'options': self._get_quiz_options(user_dict, user_dict[index][1], user_dict[index][2], 3)
                }

                quiz_data.append(question_word)
        return quiz_data

    def get_rating_list(self, limit: int, offset: int) -> list:
        query = '''SELECT users.user_id, users.user_firstname, COUNT(words.word_id) AS words_count
                   FROM words
                   INNER JOIN users ON words.user_id = users.user_id
                   GROUP BY users.user_id
                   ORDER BY words_count DESC
                   LIMIT ?
                   OFFSET ?'''
        return self._execute_query(query, limit, offset).fetchall()

    def __translate_stock_vocabulary(self, pack_size, offset):
        """TODO: REMOVE AFTER DATA PROCESSING OF THE STOCK VOCABULARY"""
        words = self.get_stock_vocabulary_words(pack_size, offset)
        for word in words:
            translation = google_translate(word[1], 'en', 'ru')
            print(word, translation)
            if translation != '' and translation is not None:
                self.set_stock_word_translation(word[0], translation)
            else:
                print('None response')
            time.sleep(5)

    def __transcribe_stock_vocabulary(self, pack_size, offset):
        """TODO: REMOVE AFTER DATA PROCESSING OF THE STOCK VOCABULARY"""
        words = self.get_stock_vocabulary_words(pack_size, offset)
        for word in words:
            leo_translation = leo_translate(word[1])
            print(leo_translation)
            if len(leo_translation['translations']) > 0:
                self.set_stock_word_translation(word[0], leo_translation['translations'][0])
            self.set_stock_word_transcription(word[0], leo_translation['transcription'])
            time.sleep(1)

    def get_stock_vocabulary_words(self, pack_size: int, offset: int):
        """TODO: REMOVE AFTER DATA PROCESSING OF THE STOCK VOCABULARY"""
        query = 'SELECT word_id, word_string FROM stock_vocabulary LIMIT ? OFFSET ?'
        return self._execute_query(query, pack_size, offset).fetchall()

    def set_stock_word_translation(self, word_id: int, word_translation: str):
        """TODO: REMOVE AFTER DATA PROCESSING OF THE STOCK VOCABULARY"""
        query = 'UPDATE stock_vocabulary SET word_translation=? WHERE word_id=?'
        self._execute_query(query, word_translation, word_id)
        self.conn.commit()

    def set_stock_word_transcription(self, word_id: int, word_transcription: str):
        """TODO: REMOVE AFTER DATA PROCESSING OF THE STOCK VOCABULARY"""
        query = 'UPDATE stock_vocabulary SET word_transcription=? WHERE word_id=?'
        self._execute_query(query, word_transcription, word_id)
        self.conn.commit()

    def search_user_word(self, user_id: int, word_string: str) -> list:
        query = 'SELECT * FROM words WHERE user_id=? AND word_string=?'
        result = self._execute_query(query, user_id, word_string).fetchall()
        return result[0] if len(result) > 0 else []
