from yates.Results.Model.ModelUtils import ResultBaseModel

from peewee import PrimaryKeyField, TextField, BooleanField, \
    BigIntegerField

class TestDetails(ResultBaseModel):
    testDetailsId = PrimaryKeyField(db_column = "id")
    testId = TextField()
    module = TextField()
    testName = TextField()
    invalid = BooleanField()
    manualInspection = BooleanField()
    docstrings = TextField()
    timeout = BigIntegerField()
