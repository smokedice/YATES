from Results.Model.ModelUtils import MasterBaseModel
from peewee import PrimaryKeyField, TextField, IntegerField, BooleanField

class Tests(MasterBaseModel):
    testId = PrimaryKeyField(db_column = 'id')
    relativePath = TextField(db_column = 'rel_path')
    testName = TextField(db_column = 'test_name')
    status = TextField()
    timeout = IntegerField()
    modulators = IntegerField()
    factoryReset = IntegerField(db_column = 'factoryreset')
    manual = BooleanField()
    environment = TextField()
    testType = TextField(db_column = 'type')
