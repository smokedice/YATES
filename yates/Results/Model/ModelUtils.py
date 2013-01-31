from datetime import datetime
from peewee import Model, SqliteDatabase, Column, Field
import time

class ResultBaseModel(Model):
    class Meta:
        database = SqliteDatabase(None , threadlocals = True)
        def __init__(self): pass

class MasterBaseModel(Model):
    class Meta:
        database = SqliteDatabase(None, threadlocals = True)
        def __init__(self): pass

class DateTimeColumn(Column):
    db_field = 'datetime'

    def get_attributes(self):
        return {}

    def db_value(self, value):
        if isinstance(value, float):
            value = datetime.fromtimestamp(value).strftime('%Y-%m-%dT%H:%M:%S')
        return Column.db_value(self, value)

    def python_value(self, value):
        if isinstance(value, basestring):
            return datetime(*time.strptime(value, '%Y-%m-%dT%H:%M:%S')[:6])
        return value

class DateTimeField(Field):
    column_class = DateTimeColumn
