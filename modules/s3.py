from pulumi import ComponentResource, ResourceOptions, Output
import pulumi_aws as aws

class BucketArgs:
    def __init__(self,
                environment=None,
                project_name=None,
                acl='private',
                versioning=False,
                principal='codebuild'
                ):
        self.environment = environment
        self.project_name = project_name
        self.acl = acl
        self.versioning = versioning
        self.principal = principal

class Bucket(ComponentResource):
    """
    Create an S3 Bucket with permissions granted to an AWS Principal
    """
    def __init__(self, name, args=BucketArgs, opts: ResourceOptions = None):
        super().__init__('pkg:index:S3', name, None, opts)
        name = "{}-{}-{}".format(name, args.project_name, args.environment)
        bucket = aws.s3.Bucket(name,
            acl=args.acl,
            versioning=aws.s3.BucketVersioningArgs(
                enabled=args.versioning,
            ),
            tags={
                "Name": name,
                "Environment": args.environment,
                "Project Name": args.project_name,
                "Managed By": 'Pulumi'
            })
        assume_role = aws.iam.Role(f"assumeRole-{name}", assume_role_policy=f"""{{
            "Version": "2012-10-17",
            "Statement": [
            {{
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {{
                    "Service": "{args.principal}.amazonaws.com"
                }}
            }}
            ]
        }}""")
        aws.iam.RolePolicy(f"bucketPolicy-{name}",
            role=assume_role.name,
            policy=Output.all(bucket=bucket.id).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                        "arn:aws:s3:::{args['bucket']}",
                        "arn:aws:s3:::{args['bucket']}/*"
                    ]
                }}
                ]
            }}"""
        ))
        self.bucket_id = bucket.id
        self.assume_role = assume_role.arn
        self.register_outputs({})