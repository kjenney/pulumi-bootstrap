import os
import sys
from github import Github

token = os.environ.get('GITHUB_TOKEN')
sha = os.environ.get('commit-sha')
state = sys.argv[1]
description = sys.argv[2]

print(sha)

g = Github(token)
repo = g.get_repo("kjenney/pulumi-bootstrap")
repo.get_commit(sha=sha).create_status(state=state,description=description)
