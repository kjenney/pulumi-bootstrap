"""Provision resources for S3 state"""

import json
import pulumi
from pulumi_aws import s3, iam

config      = pulumi.Config()
bucket_name = config.require('bucket_name')
iam_users   = config.require('iam_users')
iam_name    = config.require('iam_name')
iam_data    = config.require_object("iam")

def create_iam_role_policy_document(bucket_name):
    """
    Create the IAM policy that is attachd to the IAM role granting
    access to the state bucket
    """

    dict = {}
    dict["Version"] = "2012-10-17"
    statements = []
    statements.append({"Action":["s3:ListAllMyBuckets"],"Effect":"Allow","Resource":["arn:aws:s3:::*"]})
    statements.append({"Action":["s3:ListBucket","s3:GetBucketLocation"],"Effect":"Allow","Resource":[f"arn:aws:s3:::{bucket_name}"]})
    statements.append({"Action":["s3:GetObject","s3:PutObject"],"Effect":"Allow","Resource":[f"arn:aws:s3:::{bucket_name}/*"]})
    dict["Statement"] = statements

    return json.dumps(dict)

def create_iam_assume_role_policy_document(users):
    """
    Create the AssumeRolePolicyDocument to be attached to the IAM role granting
    access to the state bucket
    """

    dict = {}
    dict["Version"] = "2012-10-17"
    statements = []
    for u in users:
        statements.append({"Effect":"Allow","Principal":{"AWS":f"{u}"},"Action":"sts:AssumeRole"})
    dict["Statement"] = statements

    return json.dumps(dict)

# Create the S3 bucket for storing Pulumi state
bucket = s3.Bucket(bucket_name,
    bucket=bucket_name
)

# Create an IAM policy to grant access to the S3 bucket
policy = iam.Policy(iam_name,
    name=iam_name,
    path="/",
    description="Grant access to Pulumi State S3 Bucket",
    policy=create_iam_role_policy_document(bucket_name)
)

# Create an IAM trust policy for the IAM role if IAM users are defined
if iam_users == 'true':
    role = iam.Role(iam_name,
    name=iam_name,
    assume_role_policy=create_iam_assume_role_policy_document(iam_data.get('users')))
else:
    role = iam.Role(iam_name)

# Attach the IAM policy to the Role
policy_attach = iam.PolicyAttachment("policy-attach",
    roles=[role.name],
    policy_arn=policy.arn)

# Exports
pulumi.export('bucket_name', bucket.id)
pulumi.export('role_name', role.name)
pulumi.export('role_arn', role.arn)
pulumi.export('policy_arn', policy.arn)