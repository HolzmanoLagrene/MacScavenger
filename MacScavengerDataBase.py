import time

from pymongo import MongoClient


class MacScavengerDataBase:

    def __init__(self):
        client = MongoClient(serverSelectionTimeoutMS=2000)
        client.server_info()
        db = client.mac_scavenger_db
        self.db_state_handle = db['ie-ssid-registry-{}'.format(time.time_ns())]
        self.db_summary_handle = db['summary-{}'.format(time.time_ns())]

    def get_previous_appearance_ie_ssid(self, entry):
        return self.db_state_handle.find_one(check_ie_ssid_presence(entry))

    def get_previous_appearance_ie(self, entry):
        return self.db_state_handle.find_one(check_ie_presence(entry))

    def add_ssid_to_summary(self, entry):
        return self.db_summary_handle.update_one(*increase_seen_count_on_ssid(entry), upsert=True)

    def add_ssid_alias(self, latest_known_ssid, entry):
        return self.db_summary_handle.update_one(*add_summary_combination_entry(latest_known_ssid, entry['ssid']), upsert=True)

    def add_single_ssid(self, ssid):
        self.db_summary_handle.update_one(*add_summary_single_entry(ssid), upsert=True)

    def add_multiple_ssids(self, list_of_ssids):
        for ssid in list_of_ssids:
            self.add_single_ssid(ssid)

    def add_region_to_entry(self, entry, running_median, region):
        self.db_state_handle.update_one(
            *add_region_to_ie_ssid_timestamp_combination(entry, running_median, region), upsert=True
        )

    def get_document_count(self):
        return self.db_summary_handle.estimated_document_count()

    def get_uniquely_seen(self):
        return self.db_summary_handle.estimated_document_count()

    def get_non_randomizing(self):
        return self.db_summary_handle.count_documents({'seen': {'$gt': 1}})

    def get_randomizing(self):
        return self.db_summary_handle.count_documents({'alias': {'$exists': True}})


def increase_seen_count_on_ssid(entry):
    INCREASE_SEEN_COUNT_ON_SSID_SEARCH = {'ssid': entry['ssid']}
    INCREASE_SEEN_COUNT_ON_SSID_PUSH = {'$inc': {'seen': 1}}
    return INCREASE_SEEN_COUNT_ON_SSID_SEARCH, INCREASE_SEEN_COUNT_ON_SSID_PUSH


def check_ie_presence(entry):
    CHECK_IE_PRESENCE = {
        'ie': str(entry['ie'])
    }
    return CHECK_IE_PRESENCE


def check_ie_ssid_presence(entry):
    CHECK_IE_SSID_PRESENCE = {
        '$and': [
            {
                'ie': str(entry['ie'])
            }, {
                str(entry['ssid']): {
                    '$exists': True
                }
            }
        ]
    }
    return CHECK_IE_SSID_PRESENCE


def check_ie_ssid_timestamp_presence(entry, timestamp):
    CHECK_IE_SSID_TIMESTAMP_PRESENCE = {
        '$and': [
            {
                'ie': str(entry['ie'])
            }, {
                '{0}.{1}'.format(entry['ssid'], timestamp): {
                    '$exists': True
                }
            }
        ]
    }
    return CHECK_IE_SSID_TIMESTAMP_PRESENCE


def add_region_to_ie_ssid_timestamp_combination(entry, timestamp, region):
    ADD_REGION_TO_IE_SSID_TIMESTAMP_COMBINATION_SEARCH = {"ie": str(entry['ie'])}
    ADD_REGION_TO_IE_SSID_TIMESTAMP_COMBINATION_PUSH = {'$push': {'{0}.{1}'.format(entry['ssid'], timestamp): region}}
    return ADD_REGION_TO_IE_SSID_TIMESTAMP_COMBINATION_SEARCH, ADD_REGION_TO_IE_SSID_TIMESTAMP_COMBINATION_PUSH


def add_summary_single_entry(previous):
    ADD_SUMMARY_SINGLE_SEARCH = {'ssid': previous}
    ADD_SUMMARY_SINGLE_INCREASE = {'$inc': {'seen': 1}}
    return ADD_SUMMARY_SINGLE_SEARCH, ADD_SUMMARY_SINGLE_INCREASE


def add_summary_combination_entry(previous, actual):
    ADD_SUMMARY_COMBINATION_ENTRY_SEARCH = {'ssid': previous}
    ADD_SUMMARY_COMBINATION_ENTRY_PUSH = {'$addToSet': {'alias': actual}}
    return ADD_SUMMARY_COMBINATION_ENTRY_SEARCH, ADD_SUMMARY_COMBINATION_ENTRY_PUSH
