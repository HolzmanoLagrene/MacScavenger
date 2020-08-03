import json
import os
from collections import defaultdict

import pandas as pd

parent_path = '/Users/holzmano/Dropbox/Studium/FS20/Masterthesis/Experiments/Experiment 3 - Messe/data'

total_data = defaultdict(list)

for root, dirs, files in os.walk(parent_path):
    for dir in dirs:
        for root_2, dirs_2, files_2 in os.walk(root + '/' + dir):
            temp_count = 0
            for file_2 in files_2:
                if file_2.endswith('.json'):
                    with open(root_2 + '/' + file_2, 'r') as file_:
                        contents = json.load(file_)
                        total_data[dir] += (contents)
                        temp_count += len(contents)
            print('Fetched {0} datapoints from {1} files in folder {2}'
                  .format(temp_count, len(files_2), dir))

all_dfs = {}
min_data_stamps = []
for name, data in total_data.items():
    df = pd.DataFrame(data)
    df['epoch'] = df['epoch'] * 1000
    df['epoch'] = pd.to_datetime(df.epoch.astype(int), unit='ns')
    df = df.sort_values('epoch')
    min_data_stamps.append(min(df['epoch']))
    df['epoch'] = df['epoch'].apply(lambda x: x.value)
    all_dfs[name] = df

all_dfs_ = []
min_data_stamp = min(min_data_stamps).value
for name, df in all_dfs.items():
    diff = min(df['epoch']) - min_data_stamp
    df['epoch'] = df['epoch'].apply(lambda x: x-diff)
    all_dfs_.append(df)

df_total = pd.concat(all_dfs_)
df_total = df_total.sort_values('epoch')

out_path = '../json_data'

with open(out_path + '/total_data.json', 'w+') as out_:
    json.dump(df_total.to_dict('records'), out_)



# previous_pointer = 0
# pointer = previous_pointer
# size_of_slices = 1000
# count_ = 1
# while True:
#     with open(out_path+'/'+str(count_)+'.json','w+') as out_:
#         sliced_df = df.iloc[previous_pointer:pointer+size_of_slices,:]
#         json.dump(sliced_df.to_dict('records'),out_)
#     previous_pointer = pointer
#     pointer +=size_of_slices
#     count_+=1

print('Total {} datapoints'.format(len(total_data)))
