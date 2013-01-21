from Results.Model.ModelUtils import ResultBaseModel
from peewee.peewee import TextField, IntegerField, PrimaryKeyField

class TestStates(ResultBaseModel):
    stateId = PrimaryKeyField(db_column = 'id')
    name = TextField()
    sequenceId = IntegerField()
    baseType = TextField()
    description = TextField()
