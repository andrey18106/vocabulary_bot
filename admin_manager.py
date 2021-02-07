# -*- coding: utf-8 -*-

from db_manager import DbManager


class AdminManager:
    """Class for working with admin functions"""

    def __init__(self, db_manager: DbManager):
        self.db = db_manager

    def get_admin_permissions(self):
        """TODO: Implement admin permissions"""
        pass
