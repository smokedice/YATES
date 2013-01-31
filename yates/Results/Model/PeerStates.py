from Results.Model.Peer import Peer
from Results.Model.ModelUtils import DateTimeField, ResultBaseModel
from peewee import PrimaryKeyField, ForeignKeyField, TextField

class PeerStates(ResultBaseModel):
    peerStateId = PrimaryKeyField(db_column = 'peerStateId')
    peerRef = ForeignKeyField(Peer, db_column = 'peerRef', null = False)
    timestamp = DateTimeField(datetime_format = '%Y-%m-%dT%H:%M:%S')
    state = TextField()
    capabilities = TextField(null = True)
