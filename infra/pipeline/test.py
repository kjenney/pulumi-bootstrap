import argparse
import json
import pulumi
import pulumi_aws as aws
from pulumi import automation as auto
import sys
import yaml
import os

sys.path.append("../../shared")
from bootstrap import *

# Test CodePipeline Infra Deployment

def test():
    """A Test Method to see how PR testing would look"""
    print('Testing')

stack = manage(args(), os.path.basename(os.getcwd()), test)
