import pytz
import pandas as pd
import configparser
from pydriller import *
from datetime import datetime

utc = pytz.UTC

cp = configparser.RawConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
cp.read('/home/weichen/APHP/APHP-src/config/config.cfg')
desc_tags_prefixes = cp.getlist('ARR','prefixes')
neg_keywords = ['revert', 'fix compilation', 'fix compile', 'support', 'spell', 'typo', 'build error', 'checkpatch', 'gcc', 'rename', 'readability', 'indent']
keywords = cp.getlist('KEYWORD','message') + cp.getlist('KEYWORD', 'check') + cp.getlist('KEYWORD', 'errorhandling')

if __name__ == '__main__':
    df = pd.read_csv('/home/weichen/APHP/APHPatchCollect/APH_patches/APH_patches_kernelnew_v6.2.csv')
    new_df = pd.DataFrame()
    
    repo = Git('/home/weichen/linux')
    desired_date = datetime(2019, 2, 19).replace(tzinfo=utc)
    for index, row in df.iterrows():
        commit = repo.get_commit(row['hexsha'])
        commit_date = commit.committer_date
        date_1 = commit_date.replace(tzinfo=utc)
        lines = commit.msg.splitlines()
        lines_filter = list(
            filter(lambda x: not x.startswith(tuple(desc_tags_prefixes)), lines))
        desc = " ".join(lines_filter).lower().replace('-', '')
        if date_1 > desired_date and not any(keyword in desc for keyword in neg_keywords) and any((key in desc for key in keywords)):
            print(row['hexsha'], commit.committer_date)
            df_new_row = pd.DataFrame([row])
            row['time'] = date_1
            new_df = pd.concat([new_df, df_new_row], ignore_index=True)
    new_df.to_csv('/home/weichen/APHP/APHPatchCollect/APH_patches/APH_patches_kernelnew_v6.2_v1.csv', index=False)
    