from yates.Results.Model.ModelUtils import ResultBaseModel
from yates.Results.Model.Peer import Peer
from yates.Results.Model.TestStates import TestStates
from yates.Results.Model.TestDetails import TestDetails
from yates.Results.Model.TestExecutionDetails import TestExecutionDetails
from yates.Results.Model.ModelUtils import DateTimeField

from peewee import PrimaryKeyField, ForeignKeyField, BooleanField, \
    TextField, IntegerField

class TestResults(ResultBaseModel):
    resultId = PrimaryKeyField(db_column = 'resultId')
    testDetailsRef = ForeignKeyField(TestDetails,
        db_column = "testDetailsRef", null = False)
    invalid = BooleanField()
    executed = BooleanField()
    result = ForeignKeyField(TestStates, null = False, db_column = "result")
    error = TextField()
    startTime = DateTimeField(datetime_format = '%Y-%m-%dT%H:%M:%S')
    duration = IntegerField()
    manualInspection = BooleanField()
    testExecutionDetailsRef = ForeignKeyField(TestExecutionDetails,
        db_column = 'testExecutionDetailsRef', null = False)
    peerRef = ForeignKeyField(Peer, db_column = 'peerRef', null = True)
    iterationId = TextField(null = True)
