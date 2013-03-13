from yates.Results.Model.ModelUtils import ResultBaseModel
from yates.Results.Model.ModelUtils import DateTimeField

from peewee import PrimaryKeyField, TextField, CharField, IntegerField

class TestExecutionDetails(ResultBaseModel):
    executionId = PrimaryKeyField(db_column = 'executionId')
    testSuiteName = CharField()
    executionName = TextField()
    shortFilterDesc = CharField()
    testPackDescriptor = TextField()
    startTime = DateTimeField(datetime_format = '%Y-%m-%dT%H:%M:%S')
    endTime = DateTimeField(datetime_format = '%Y-%m-%dT%H:%M:%S')
    duration = IntegerField()
    envservExecutionModeName = CharField()
    hostNetAddress = CharField()
    hostMacAddress = CharField()
    tasVersion = CharField()
    scmidentifier = CharField(db_column = 'scmIdentifier')
