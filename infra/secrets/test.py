import sys
import os
import pulumi

sys.path.append("../../shared")
from bootstrap import manage, args

# Test Secrets Infra

def test():
    """A Test Method to see how PR testing would look"""
    config = pulumi.Config()
    environment = config.require('environment')
    print(environment)

stack = manage(args(), os.path.basename(os.getcwd()), test)
