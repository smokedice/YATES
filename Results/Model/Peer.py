from Results.Model.ModelUtils import ResultBaseModel
from peewee.peewee import PrimaryKeyField, CharField

class Peer(ResultBaseModel):
    peerId = PrimaryKeyField(db_column = 'id')
    macAddress = CharField()
    netAddress = CharField()
