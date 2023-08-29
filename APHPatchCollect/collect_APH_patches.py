from git import Repo
from pydriller import *
import pandas as pd
import click
import configparser
from rich.progress import track
import os


# read config from files
cp = configparser.RawConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
cp.read('/home/weichen/APHP/APHP-src/config/config.cfg')
keywords = cp.getlist('KEYWORD','message') + cp.getlist('KEYWORD', 'check') + cp.getlist('KEYWORD', 'errorhandling')
PATCH_DIR = cp.get('DATA_PATH','patch')
neg_keywords = ['revert', 'fix compilation', 'fix compile', 'add support', 'spell', 'typo']
desc_tags_prefixes = cp.getlist('ARR','prefixes')

class APHPatchCollector:
    def __init__(self,repo_name) -> None:
        self.repo_name = repo_name
        self.source_dir = cp.get('URL',repo_name)
        self.repo = Repo(self.source_dir)
        self.repo1 = Git(self.source_dir)
        self.commit_url = cp.get('COMMITURL',repo_name)
        self.get_APH_patches()
        # print(self.check_is_related_to_APH('56a468b5f6454aae0e32e4c6ead1abde5cc4dd23'))
    
    
    def get_APH_patches(self):
        branch = cp.get('BRANCH',self.repo_name)
        print("Collecting patches potentially relted to APH bugs in" , self.repo_name, branch)
        patch_file_path = os.path.join(PATCH_DIR, f'APH_patches_{self.repo_name}_{branch}.csv')
        # 2019/02/19-2023/02/19 commits in v6.2
        idlist = list(
                self.repo.iter_commits(
                    branch, max_count=384325, no_merges=True,
                )
            )
        df = pd.DataFrame()
        print(f"Processing all the patches to find suspects, total patch number is: {len(idlist)}")
        for i in track(idlist):
            patch = f"{self.commit_url}{i.hexsha[:12]}"
            if self.check_is_related_to_APH(i.hexsha[:12]):
                item = {"hexsha": i.hexsha[:12], "patch": patch, "summary": i.summary, "author": i.author.name}

                df_new_row = pd.DataFrame([item])
                df = pd.concat([df,df_new_row],ignore_index=True)
        print(f"Done, the collected patch is {len(df)}, save to file " + patch_file_path)
        df.to_csv(patch_file_path, index=False)

        
    def check_is_related_to_APH(self,hexsha):
        return bool((self.check_patch_description(hexsha) and self.check_code_changes(hexsha)
                      and self.check_if_driver(hexsha)))
    

    def check_code_changes(self,hexsha):
        commit = self.repo1.get_commit(hexsha)
        if commit.files>5 or commit.insertions>30 or commit.deletions>30:
            return False

        # func-level check: no modification for func or too many funcs
        modified_func = []
        for f in commit.modified_files:
            modified_func.extend(method.name for method in f.changed_methods)
        
        return len(modified_func) >= 1 and len(modified_func) <= 5        

    def check_patch_description(self, hexsha):
        commit = self.repo1.get_commit(hexsha)
        lines = commit.msg.splitlines()
        lines_filter = list(
            filter(lambda x: not x.startswith(tuple(desc_tags_prefixes)), lines))
        desc = " ".join(lines_filter)
        desc = desc.lower()
        if any(keyword in desc for keyword in neg_keywords):
            return False
        return any((key in desc for key in keywords))
    
    def check_if_driver(self,hexsha):
        commit = self.repo1.get_commit(hexsha)
        for f in commit.modified_files:
            if f.new_path and not f.new_path.startswith("drivers/") \
                and not f.new_path.startswith("sound/"):
                return False
        return True
                    
    
    def check_if_ccstable(self, hexsha):
        commit = self.repo1.get_commit(hexsha)
        lines = commit.msg.splitlines()
        lines_filter = list(filter(lambda x: x.startswith(tuple(desc_tags_prefixes)), lines))
        for line in lines_filter:
            if 'stable@vger.kernel.org' in line:
                return True
            if 'stable@kernel.org' in line:
                return True
        return False
        


@click.group()
def cli():
    pass


@cli.command('one')
@click.argument('repo_name')
def collect_one_repo(repo_name):
    APHPatchCollector(repo_name)

 

# example: python get_api_misuse_commit.py one redis
if __name__ == '__main__':
    cli()

    



