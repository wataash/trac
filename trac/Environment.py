# -*- coding: iso8859-1 -*-
#
# Copyright (C) 2003, 2004 Edgewall Software
# Copyright (C) 2003, 2004 Jonas Borgstr�m <jonas@edgewall.com>
#
# Trac is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Trac is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Jonas Borgstr�m <jonas@edgewall.com>
#
# Todo: Move backup and upgrade from db.py
#

import os
import ConfigParser

import db_default

import sqlite

class Environment:
    """
    Trac stores project information in a Trac environment.

    A Trac environment consists of a directory structure containing
    among other things:
     * a configuration file.
     * a sqlite database (stores tickets, wiki pages...)
     * Project specific templates and wiki macros.
     * wiki and ticket attachments.
    """
    def __init__(self, path, create=0):
        self.path = path
        if create:
            self.create()
        self.verify()
        self.load_config()

    def verify(self):
        """Verifies that self.path is a compatible trac environment"""
        fd = open(os.path.join(self.path, 'VERSION'), 'r')
        assert fd.read(26) == 'Trac Environment Version 1'
        fd.close()

    def get_db_cnx(self):
        db_str = self.get_config('trac', 'database', 'sqlite:db/trac.db')
        assert db_str[:7] == 'sqlite:'
        db_name = os.path.join(self.path, db_str[7:])
        if not os.access(db_name, os.F_OK):
            raise EnvironmentError, 'Database "%s" not found.' % db_name
        
        directory = os.path.dirname(db_name)
        if not os.access(db_name, os.R_OK + os.W_OK) or \
               not os.access(directory, os.R_OK + os.W_OK):
            raise EnvironmentError, \
                  'The web server user requires read _and_ write permission\n' \
                  'to the database %s and the directory this file is located in.' % db_name
        return sqlite.connect(os.path.join(self.path, db_str[7:]),
                              timeout=10000)

    def create(self):
        # Create the directory structure
        os.mkdir(self.path)
        os.mkdir(os.path.join(self.path, 'conf'))
        os.mkdir(os.path.join(self.path, 'db'))
        os.mkdir(os.path.join(self.path, 'attachments'))
        os.mkdir(os.path.join(self.path, 'templates'))
        os.mkdir(os.path.join(self.path, 'wiki-macros'))
        # Create a few static files
        fd = open(os.path.join(self.path, 'VERSION'), 'w')
        fd.write('Trac Environment Version 1\n')
        fd = open(os.path.join(self.path, 'README'), 'w')
        fd.write('This directory contains a Trac project.\n'
                 'Visit http://trac.edgewall.com/ for more information.\n')
        fd = open(os.path.join(self.path, 'conf', 'trac.ini'), 'w')
        fd.close()
        cnx = sqlite.connect(os.path.join(self.path, 'db', 'trac.db'))
        cursor = cnx.cursor()
        cursor.execute(db_default.schema)
        cnx.commit()

    def insert_default_data(self):
        def prep_value(v):
            if v == None:
                return 'NULL'
            else:
                return '"%s"' % v
        cnx = self.get_db_cnx()
        cursor = cnx.cursor()
        
        for t in xrange(0, len(db_default.data)):
            table = db_default.data[t][0]
            cols = ','.join(db_default.data[t][1])
            for row in db_default.data[t][2]:
                values = ','.join(map(prep_value, row))
                sql = "INSERT INTO %s (%s) VALUES(%s);" % (table, cols, values)
                cursor.execute(sql)
        for s,n,v in db_default.default_config:
            if not self.cfg.has_section(s):
                self.cfg.add_section(s)
            self.cfg.set(s, n, v)
        self.save_config()
        cnx.commit()

    def get_version(self):
        cnx = self.get_db_cnx()
        cursor = cnx.cursor()
        cursor.execute("SELECT value FROM system"
                       " WHERE name='database_version'")
        row = cursor.fetchone()
        return row and int(row[0])

    def load_config(self):
        self.cfg = ConfigParser.ConfigParser()
        self.cfg.read(os.path.join(self.path, 'conf', 'trac.ini'))

    def get_config(self, section, name, default=''):
        if not self.cfg.has_option(section, name):
            return default
        return self.cfg.get(section, name)

    def set_config(self, section, name, value):
        """Changes a config value, these changes are _not_ persistent
        unless saved with save_config()"""
        return self.cfg.set(section, name, value)

    def save_config(self):
        self.cfg.write(open(os.path.join(self.path, 'conf', 'trac.ini'), 'w'))

    def get_templates_dir(self):
        return os.path.join(self.path, 'templates')
    
    def get_attachments_dir(self):
        return os.path.join(self.path, 'attachments')
