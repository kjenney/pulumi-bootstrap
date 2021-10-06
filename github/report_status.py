import os
import sys
from github import Github

token = os.environ.get('GITHUB_TOKEN')
commit_sha = os.environ.get('commit-sha')
state = sys.argv[1]
description = sys.argv[2]

g = Github(token)
repo = g.get_repo("kjenney/pulumi-bootstrap")
repo.get_commit(sha=commit_sha).create_status(state=state,description=description)
