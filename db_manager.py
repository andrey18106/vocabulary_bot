# -*- coding: utf-8 -*-

# TODO: Add user restrictions according to API limits
# TODO: (new words per day, total vocabulary capacity, available number of quizzes, number of instant translations)
# TODO: Create Glossary database structure (for reducing API usage because of its limits)

# ===== Default imports =====

from datetime import datetime
import logging
import os
import sqlite3


class DbManager:
    """Class for working with bot database"""

    conn = None  # Connection to SQLite3 database

    def __init__(self, path_to_db: str):

        self.path_to_db = path_to_db

    def create_connection(self):
        """Connect to SQLite database"""
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
        """Close the connection (e.g. after shutdown the bot)"""
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
        """Create database structure"""
        users_table = '''CREATE TABLE users (
                            user_id INT PRIMARY KEY NOT NULL, 
                            user_nickname STRING, 
                            user_firstname STRING, 
                            user_lastname STRING, 
                            lang TEXT,
                            date_added DATETIME,
                            referrals INT DEFAULT (0) 
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
        """Check if user exists in database by unique id"""
        query = 'SELECT * FROM users WHERE user_id=?'
        return len(self._execute_query(query, user_id).fetchall()) > 0

    def add_user(self, user_id: int, user_nickname: str, user_firstname: str, user_lastname: str) -> None:
        """Adding a new user to the database"""
        query = '''INSERT INTO users (user_id, user_nickname, user_firstname, user_lastname, date_added) 
                   VALUES(?, ?, ?, ?, ?)'''
        self._execute_query(query, user_id, user_nickname, user_firstname, user_lastname, datetime.now().date())
        self.conn.commit()

    def get_user_lang(self, user_id: int) -> str:
        """Returns user language setting"""
        query = 'SELECT lang FROM users WHERE user_id=?'
        result = self._execute_query(query, user_id).fetchall()
        if len(result) > 0:
            return str(result[0][0])

    def set_user_lang(self, user_id: int, user_lang: str) -> None:
        """Update user language setting in database"""
        query = 'UPDATE users SET lang=? WHERE user_id=?'
        self._execute_query(query, user_lang, user_id)
        self.conn.commit()

    def add_metric(self, metric_name):
        """Creates metric record in database"""
        query = 'INSERT INTO metrics (metric_name) VALUES (?)'
        self._execute_query(query, metric_name)
        self.conn.commit()

    def metric_exists(self, metric_id: int) -> bool:
        """Check if metric exists"""
        query = 'SELECT metric_id FROM metrics WHERE metric_id=?'
        return len(self._execute_query(query, metric_id).fetchall()) > 0

    def metric_name_exists(self, metric_name: str) -> bool:
        """Check if metric exists
        TODO: Add usage of this method
        """
        query = 'SELECT metric_id FROM metrics WHERE metric_name=?'
        return len(self._execute_query(query, metric_name).fetchall()) > 0

    def get_metric_id(self, metric_name: str) -> int:
        """Returns metric id by metric name"""
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
        """Saves the message metrics to the database"""
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
        """Saves the callback metrics to the database"""
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
        """Check if user is admin"""
        query = 'SELECT user_id FROM admins WHERE user_id=?'
        return len(self._execute_query(query, user_id).fetchall()) > 0

    def get_permissions_list(self) -> list:
        """Returns list of admin permissions"""
        query = 'SELECT * FROM permissions'
        return self._execute_query(query).fetchall()[0]

    def get_user_dict(self, user_id: int) -> list:
        """TODO: Implement user dict in database"""
        query = 'SELECT word_id, word_string, word_translation, from_lang, to_lang FROM words WHERE user_id=?'
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

    def get_user_dict_info(self, user_id: int) -> int:
        query = 'SELECT * FROM words WHERE user_id=?'
        return len(self._execute_query(query, user_id).fetchall())

    def get_user_referral_count(self, user_id: int) -> int:
        query = 'SELECT referrals FROM users WHERE user_id=?'
        return self._execute_query(query, user_id).fetchall()[0][0]

    def update_referral_count(self, user_id: int):
        query = 'UPDATE users SET referrals=? WHERE user_id=?'
        self._execute_query(query, self.get_user_referral_count(user_id) + 1, user_id)
        self.conn.commit()
