import json
from collections import defaultdict
from hashlib import sha1

import pandas as pd
from streamz import Stream, glob

from MacScavengerDataBase import MacScavengerDataBase
from MacScavengerLocalizer import MacScavengerLocalizer


class ScavengerAnalyzer:
    def __init__(self, ap_data, time_interval_in_s=10, assumed_walking_speed_km_per_h=2, in_burst_threshold_in_s=1, min_device_detection_rate=3, verbosity=0):
        self.Localizer = MacScavengerLocalizer(ap_data)
        self.database = MacScavengerDataBase()
        self.time_interval_in_s = time_interval_in_s
        self.assumed_walking_speed_km_per_h = assumed_walking_speed_km_per_h
        self.running_median = None
        self.in_burst_threshold_in_s = in_burst_threshold_in_s
        self.min_device_detection_rate = min_device_detection_rate
        self.verbosity = verbosity

    def get_config(self):
        return self.time_interval_in_s, self.assumed_walking_speed_km_per_h, self.in_burst_threshold_in_s, self.min_device_detection_rate, self.verbosity

    def print(self, text):
        if self.verbosity == 1:
            print(text)

    def start(self, data_path):
        source = Stream()
        pipe = source \
            .map(self._load_json) \
            .map(pd.DataFrame) \
            .map(self._parse_timestamp) \
            .accumulate(self._create_even_intervals, returns_state=True, start=pd.DataFrame()) \
            .flatten() \
            .map(self._create_hash) \
            .map(self._intersect_overlapping) \
            .filter(lambda x: x is not None and len(x) > 0) \
            .map(self._group_ies_and_ssids) \
            .map(self._localize) \
            .map(self._interpret_results) \
            .sink(self._to_database)
        for fn in glob(data_path):
            source.emit(fn)

    def _load_json(self, path):
        with open(path, 'r+') as inp_:
            return json.load(inp_)

    def _parse_timestamp(self, data_frame):
        data_frame['epoch'] = pd.to_datetime(data_frame.epoch.astype(int), unit='ns')
        return data_frame

    def _create_even_intervals(self, state, data_frame):
        new_data_frame = state.append(data_frame)
        intervals = (new_data_frame.epoch - new_data_frame.epoch[0]).astype('timedelta64[{}s]'.format(self.time_interval_in_s))
        split_data_frame = [g.reset_index(drop=True) for i, g in new_data_frame.groupby([intervals])]
        if len(split_data_frame) > 1:
            return pd.DataFrame(), split_data_frame
        else:
            return new_data_frame, []

    def _create_hash(self, data_frame):
        data_frame['hash'] = data_frame['ie'] + data_frame['ssid']
        data_frame['hash'] = data_frame['hash'].apply(lambda x: sha1(str(x).encode('utf-8')).hexdigest())
        return data_frame

    def _intersect_overlapping(self, data_frame):
        distinct_devices = list(data_frame.ap.unique())
        dfs = [data_frame[data_frame['ap'] == ap] for ap in distinct_devices]
        if len(dfs) >= self.min_device_detection_rate:
            intersect_hash = set(dfs[0]['hash']).intersection(*[set(df['hash']) for df in dfs[1:]])
            intersect_dfs = [df[df['hash'].isin(intersect_hash)] for df in dfs]
            intersect_dfs_list = [intersect_df.drop('hash', axis=1) for intersect_df in intersect_dfs]
            new_df = pd.concat(intersect_dfs_list)
            if len(new_df) > 0:
                return new_df
            else:
                return None
        else:
            return None

    def _group_ies_and_ssids(self, data_frame):
        def extend_lists(data):
            result = defaultdict(list)
            for list_ in data:
                k, v = list_[0], list_[1]
                result[k].extend([v])
            return dict(result)

        dates = list(data_frame.sort_values('epoch')['epoch'])
        self.running_median = dates[len(dates) // 2].value
        df_agg = data_frame.groupby(['ie', 'ssid'])[['ap', 'rssi']].apply(lambda g: g.values.tolist()).apply(lambda x: extend_lists(x)).reset_index(name='measurement')
        return df_agg

    def _localize(self, data_frame):
        data_frame['localization'] = data_frame['measurement'].apply(lambda x: self.Localizer.localize(x))
        data_frame = data_frame.drop('measurement', axis=1)
        return data_frame

    def _interpret_results(self, data_frame):
        for entry in data_frame.to_dict(orient='records'):
            previous_appearance = self.database.get_previous_appearance_ie_ssid(entry)
            if previous_appearance:
                previous_most_recent_timestamp = int(max(list(previous_appearance[entry['ssid']].keys())))
                if self.running_median - previous_most_recent_timestamp < self.in_burst_threshold_in_s * 1e+9:
                    self.print('Combination of IE and SSID has been seen before. Could be of same burst though')
                else:
                    self.database.add_ssid_to_summary(entry)
                    self.print('Combination of IE and SSID has been seen before. Most probably not of same burst. SSID most likely non-randomized')
            else:
                equal_ie = self.database.get_previous_appearance_ie(entry)
                if equal_ie:
                    self.print('Known Pattern of IEs ... Starting Location based Analysis:')
                    del equal_ie['_id']
                    del equal_ie['ie']
                    latest_entry = max([max(v.keys()) for k, v in equal_ie.items()])
                    time_since_latest_entry = int((self.running_median - int(latest_entry)) / 1e+9)
                    latest_known_ssid, latest_regions_of_presence = [(k, v[latest_entry]) for k, v in equal_ie.items() if latest_entry in v.keys()][0]
                    if time_since_latest_entry < 0:
                        raise Exception()
                    is_possible_equal, previous, actual, distance = self.Localizer.is_equal(
                        latest_regions_of_presence, entry['localization'], time_since_latest_entry, self.assumed_walking_speed_km_per_h
                    )
                    if is_possible_equal:
                        self.database.add_ssid_alias(latest_known_ssid, entry)
                        self.print('Most likely {0} and {1} are the same SSID. '
                                   '\nThe regions {2} and {3} are close enough for that:\nWith a walking speed of {4} km/h a distance of {5} meters can be done in {6} seconds'
                                   .format(latest_known_ssid, entry['ssid'], previous, actual, self.assumed_walking_speed_km_per_h, distance, time_since_latest_entry))
                    else:
                        self.database.add_multiple_ssids([latest_known_ssid, entry['ssid']])
                        self.print('Most likely {0} and {1} are the not same SSID'
                                   '\nNone of their possible locations is close enough:\nWith a walking speed of {2} km/h a distance of {3} meters cant be done in {4} seconds)'
                                   .format(latest_known_ssid, entry['ssid'], self.assumed_walking_speed_km_per_h, distance, time_since_latest_entry))
                else:
                    self.database.add_single_ssid(entry['ssid'])
                    self.print('So far IE never seen before. Adding to Database.')
        return data_frame

    def _to_database(self, data):
        for entry in data.to_dict(orient='records'):
            for region in entry['localization']:
                self.database.add_region_to_entry(entry, self.running_median, region)

    def summary(self):
        unqiue_ids = self.database.get_document_count()
        uniquely_seen_ids = self.database.get_uniquely_seen()
        non_randomizing_devices = self.database.get_non_randomizing()
        randomizing_devices = self.database.get_randomizing()

        print('Summary:')
        print('Approximately {0} different recognizable devices on site that were detected by at minimum {1} APs'.format(unqiue_ids, self.min_device_detection_rate))
        print('Thereof, {0} devices were seen just once, while {1} were seen multiple times'.format(uniquely_seen_ids, non_randomizing_devices + randomizing_devices))
        print('{0} devices were using MAC Randomization, {1} were not applying Randomization techniques'.format(randomizing_devices, non_randomizing_devices))


if __name__ == '__main__':
    ap_data = {'tinkerboard1': (0, 0), 'tinkerboard2': (8, 0), 'tinkerboard3': (8, 5), 'tinkerboard4': (0, 5)}
    scavAnalyzer = ScavengerAnalyzer(ap_data)
    scavAnalyzer.time_interval_in_s = 20
    scavAnalyzer.start('json_data/*.json')
    scavAnalyzer.summary()
