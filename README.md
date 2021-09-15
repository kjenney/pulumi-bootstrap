# pulumi-bootstrap

## What is this for?

To Deploy Infrastructure on AWS using Pulumi while keeping secrets encrypted in code.

---

## Why do we do this?

Because we always expect our Infrastructure and Secrets will get out of control. By keeping secrets encrypted in code this allows us to audit, rotate, version, and test them. Pulumi extends pure code so we can build stacks that are highly extensible.

---

## What do we use?

* [Pulumi](https://www.pulumi.com/)
* [Pulumi's Automation API](https://www.pulumi.com/docs/guides/automation-api/)
* [AWS](https://aws.amazon.com/)
* [Python](https://www.python.org/)
* [KMS](https://aws.amazon.com/kms/)
* [AWS CLI](https://aws.amazon.com/cli/)
* [aws-vault (*Optional*)](https://github.com/99designs/aws-vault)

---

## What do you need to get started?

1. At least one AWS Account
1. At least one IAM user per AWS account
1. Python 3 installed locally
1. The AWS CLI installed locally
1. A method to securely pass IAM credentials to a Python script (we recommend using [aws-vault](https://github.com/99designs/aws-vault))
1. A Pulumi CLI installation ([v3.0.0](https://www.pulumi.com/docs/get-started/install/versions/) or later)

---

## How do you get started?

Once you've got all the prerequisites taken care of you'll need to provision the following resources:

1. An S3 Bucket to be used for keeping Pulumi state
1. An IAM role to assume to to access the bucket
1. A KMS key for encrypting secrets in state that one or more IAM users have access to
1. An encryption key for encrypting secrets in Git

To provision all of these things we'll use the Pulumi service without the Automation API. 

If you want to allow one or more IAM users to assume the bucket role you need to set `iam_users` to `true` and add them. There are examples below.

`iam_name` will be the name of the IAM role and IAM policy granting access to the bucket.

## Create S3 Shared State with IAM permissions

We'll start out by deploying required resources in a single AWS account. If you want to allow users in other AWS accounts to access the bucket check out the [Next Steps](#next-steps)

1. ```shell
   cd shared-state
   ```
1. Create a new stack in your account:
   ```shell
   pulumi config
   ```
1. Set configuration options for stack. Change the values to meet your needs:
   Required:
   ```shell
   pulumi config set bucket_name                my-pulumi-state
   pulumi config set iam_users                  true
   pulumi config set iam_name                   AccessPulumiStateBucket
   ```

   Optional:
   ```shell
   pulumi config set --path iam.users[0]        arn:aws:iam::213597402033:user/user1
   pulumi config set --path iam.users[1]        arn:aws:iam::213597402033:user/user2
   ```

To provision the resources you need to run:
```shell
pulumi up
```
or

```shell
aws-vault exec {{some-profile}} -- pulumi up
```

## Deploying CodePipeline

We'll deploy a CodePipeline which will in turn deploy all of the infrastructure we need in our environment - including updating the existing CodePipeline when changes are commited.


## Next Steps

Create an IAM policy and attach to an IAM user in another account to give the user access to manage state for that account. The IAM policy can be imported to a stack once the user has access to the state bucket.

Keep `encrypted_secret.key` handy for future work.

