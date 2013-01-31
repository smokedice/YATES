from Results.Model.ModelUtils import ResultBaseModel
from Results.Model.Peer import Peer
from Results.Model.TestStates import TestStates
from TestDetails import TestDetails
from TestExecutionDetails import TestExecutionDetails
from peewee.peewee import PrimaryKeyField, ForeignKeyField, BooleanField, \
    TextField, IntegerField
from ModelUtils import DateTimeField

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
