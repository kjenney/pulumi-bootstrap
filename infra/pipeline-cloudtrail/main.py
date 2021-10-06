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

# Deploy CloudTrail Trail to track S3 events

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    s3_stack = pulumi.StackReference(f"pipeline-s3-{environment}")
    codebuild_functional_bucket = s3_stack.get_output("codebuild_functional_bucket")
    codebuild_main_bucket = s3_stack.get_output("codebuild_main_bucket")

        # Create CloudTrail Trail to track S3 Events
    current = aws.get_caller_identity()
    pipeline_s3_trail_bucket = aws.s3.Bucket(f"s3trail-{environment}")
    pipeline_s3_trail_bucket_policy = aws.s3.BucketPolicy("s3_trail_bucket_policy",
        bucket=pipeline_s3_trail_bucket.id,
        policy=pulumi.Output.all(pipeline_s3_trail_bucket=pipeline_s3_trail_bucket.id).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Sid": "AWSCloudTrailAclCheck20150319",
                    "Effect": "Allow",
                    "Principal": {{
                        "Service": "cloudtrail.amazonaws.com"
                    }},
                    "Action": "s3:GetBucketAcl",
                    "Resource": "arn:aws:s3:::{args['pipeline_s3_trail_bucket']}"
                }},
                {{
                    "Sid": "AWSCloudTrailWrite20150319",
                    "Effect": "Allow",
                    "Principal": {{
                        "Service": "cloudtrail.amazonaws.com"
                    }},
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::{args['pipeline_s3_trail_bucket']}/AWSLogs/{current.account_id}/*",
                    "Condition": {{
                        "StringEquals": {{
                            "s3:x-amz-acl": "bucket-owner-full-control"
                        }}
                    }}
                }}
            ]
            }}
    """))
    s3_trail = aws.cloudtrail.Trail("pipeline_s3_trail",
        s3_bucket_name=pipeline_s3_trail_bucket.id,
        event_selectors=[aws.cloudtrail.TrailEventSelectorArgs(
            read_write_type="All",
            include_management_events=True,
            data_resources=[aws.cloudtrail.TrailEventSelectorDataResourceArgs(
                type="AWS::S3::Object",
                values=[codebuild_functional_bucket.apply(lambda id: f"arn:aws:s3:::{id}/buildspec.yml"),codebuild_main_bucket.apply(lambda id: f"arn:aws:s3:::{id}/buildspec.yml")]
            )],
        )])

stack = manage(args(), os.path.basename(os.getcwd()), pulumi_program)


