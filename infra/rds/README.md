# pulumi-bootstrap-rds

Provision an Aurora RDS instance complete with tables

## Getting Started

You'll need to ensure that you've completed everything in https://github.com/kjenney/pulumi-bootstrap

First, set up your virtual environment:
1. ```shell
   python3 -m venv venv
   ```
2. ```shell
   venv/bin/python3 -m pip install --upgrade pip
   ```
3. ```shell
   venv/bin/pip install -r requirements.txt
   ```
Running this program is just like any other python program. No invocation through the Pulumi CLI required:

```shell
python3 main.py -b {your-pulumi-state-s3-bucket} -k {your-pulumi-kms-alias} -n rds -s {environment}
```

To destroy resources provisioned by the stack use:

```shell
python3 main.py -b {your-pulumi-state-s3-bucket} -k {your-pulumi-kms-alias} -n rds -s {environment} --destroy
```