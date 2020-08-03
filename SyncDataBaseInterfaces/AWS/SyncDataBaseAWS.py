import os

from SyncDataBaseInterfaces.SyncDataBaseBaseClass import SyncDataBaseBaseclass


class SyncDataBaseAWS(SyncDataBaseBaseclass):
    def __init__(self):
        super().__init__()
        import pandas as pd
        import boto3
        access_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'accessKeys.csv')
        credentials = pd.read_csv(access_file)
        session = boto3.Session(credentials['Access key ID'].iloc[0], credentials['Secret access key'].iloc[0])
        session.get_credentials()
        self.s3 = session.resource('s3')

    def write(self, data):
        import json
        from_ = min([data_['epoch'] for data_ in data])
        to_ = max([data_['epoch'] for data_ in data])
        self.s3.meta.client.put_object(
            Body=json.dumps(data),
            Bucket='testbucketlenz',
            Key='upload_folder/{0}-{1}.json'.format(from_, to_)
        )
