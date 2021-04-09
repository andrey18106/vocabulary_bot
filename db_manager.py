# -*- coding: utf-8 -*-

# ===== Default imports =====

from config import DEFAULT_LANG
from datetime import datetime
import logging
import os
import random
import sqlite3
from shutil import copyfile

# ===== Local imports =====

from itertools import islice


class DbManager:
    """Class for working with bot database"""

    conn = None  # Connection to SQLite3 database

    def __init__(self, path_to_db: str, dev_mode: bool):
        self.dev_mode = dev_mode
        self.path_to_db = path_to_db
        self.path_to_sql_dump = str(path_to_db).replace('db', 'sql')
        if self.dev_mode:
            path_to_db_dev = str(path_to_db).replace('.db', '_dev.db')
            copyfile(path_to_db, path_to_db_dev)
            self.path_to_db = path_to_db_dev

    def create_connection(self):
        try:
            self.conn = sqlite3.connect(self.path_to_db)
            if not self._database_created():
                self._init_database()
            logging.getLogger(type(self).__name__).info(
                f' SQLite {sqlite3.version} database successfully loaded '
                f'[size: {round(os.path.getsize(self.path_to_db) / 1000)} KB]')
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
                  'achievements_log', 'stock_vocabulary']
        query = '''SELECT name FROM sqlite_master WHERE type='table' AND name=?;'''
        result = True
        for table_name in tables:
            result &= len(self._execute_query(query, table_name).fetchall()) > 0
        return result

    def _init_database(self) -> None:
        try:
            with open(self.path_to_sql_dump, 'r', encoding='utf-8') as sql_file:
                self.conn.executescript(sql_file.read())
            logging.getLogger(type(self).__name__).info('Database structure successfully created')
        except sqlite3.Error as error:
            logging.getLogger(type(self).__name__).error(f'Error while creating database.\n{error}')

    def _execute_query(self, query: str, *args) -> sqlite3.Cursor:
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

    def add_metric(self, metric_name: str):
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
        return self._execute_query(query).fetchall()

    def get_admin_permission_level(self, user_id: int) -> int:
        query = 'SELECT permission_level FROM admins WHERE user_id=?'
        return self._execute_query(query, user_id).fetchall()[0][0]

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

    def update_user_word_string(self, user_id: int, word_id: int, word_string: str):
        query = 'UPDATE words SET word_string=? WHERE user_id=? AND word_id=?'
        self._execute_query(query, word_string, user_id, word_id)
        self.conn.commit()

    def update_user_word_translation(self, user_id: int, word_id: int, word_translation: str):
        query = 'UPDATE words SET word_translation=? WHERE user_id=? AND word_id=?'
        self._execute_query(query, word_translation, user_id, word_id)
        self.conn.commit()

    def get_user_word_by_str(self, word_string: str, user_id: int) -> int:
        query = 'SELECT word_id FROM words WHERE user_id=? AND word_string=?'
        result = self._execute_query(query, user_id, word_string).fetchall()
        return result[0][0] if len(result) > 0 else None

    def delete_user_word(self, word_id: int, user_id: int):
        query = 'DELETE FROM words WHERE word_id=? AND user_id=?'
        self._execute_query(query, word_id, user_id)
        self.conn.commit()

    def get_broadcast_users(self, mailings: int = 2) -> list:
        query = 'SELECT user_id FROM users WHERE mailings=?'
        result = self._execute_query(query, mailings).fetchall()
        return map(lambda item: item[0], result) if len(result) > 0 else []

    @staticmethod
    def _stat_pages(data: dict, size: int = 10):
        it = iter(data)
        for i in range(0, len(data), size):
            yield {k: data[k] for k in islice(it, size)}

    def get_user_dict_last_word_date(self, user_id: int) -> datetime:
        query = 'SELECT date_added FROM words WHERE user_id=? ORDER BY date_added ASC'
        query_result = self._execute_query(query, user_id).fetchall()[0][0].split('-')
        result = datetime(int(query_result[0]), int(query_result[1]), int(query_result[2]))
        return result

    def get_user_dictionary_stats(self, user_id: int) -> dict:
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

    @staticmethod
    def _get_quiz_options(user_dict: list, word_string: str, word_translation: str, amount: int) -> list:
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

    def search_user_word(self, user_id: int, word_string: str) -> list:
        query = 'SELECT * FROM words WHERE user_id=? AND word_string=?'
        result = self._execute_query(query, user_id, word_string).fetchall()
        return result[0] if len(result) > 0 else []

    def get_user_achievements(self, user_id: int) -> list:
        query = 'SELECT * FROM achievements WHERE user_id=?'
        return self._execute_query(query, user_id).fetchall()
