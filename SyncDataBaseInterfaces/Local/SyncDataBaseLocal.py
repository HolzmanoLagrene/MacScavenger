import os

from SyncDataBaseInterfaces.SyncDataBaseBaseClass import SyncDataBaseBaseclass


class SyncDataBaseLocal(SyncDataBaseBaseclass):
    def __init__(self):
        super().__init__()

    def write(self, data):
        import json
        from_ = min([data_['epoch'] for data_ in data])
        to_ = max([data_['epoch'] for data_ in data])
        with open('{0}-{1}.json'.format(from_, to_),'a+') as out_:
            json.dump(data,out_)
