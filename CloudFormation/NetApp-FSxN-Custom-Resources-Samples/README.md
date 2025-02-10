# NetApp FSxN Third Party CloudFormation Extensions Examples

## Overview
This repository contains example CloudFormation templates that use the NetApp FSxN Third Party CloudFormation Extensions.

It also contains shell scripts that can be used to get you started quickly, as well as some shell
scripts that allow you to deploy these examples with the AWS CLI.

And, as a bonus, there is one Python script that can be used to create a clone of an existing FSx for NetApp ONTAP volume.

## Prerequisites
### Get a Preview Key
- The first thing you need to do before you can use any of the NetApp FSxN Third Party CloudFormation Extensions is obtain a `preview key`.
You can get one of those by sending an email to [Ng-fsx-cloudformation@netapp.com](mailto:Ng-fsx-cloudformation@netapp.com) requesting one.

## Getting Started
Once you have the preview key, you are ready to activate the extensions and start using them.

### Step 1 Create an IAM role
You need to create an IAM role that the extensions will assume to create and/or modify resources on your behalf.
The following is a CloudFormation template that you can use to create the role:
```
AWSTemplateFormatVersion: "2010-09-09"
Description: >
  This CloudFormation template creates a role assumed by CloudFormation
  during CRUDL operations to mutate resources on your behalf.

Resources:
  ExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      MaxSessionDuration: 8400
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: resources.cloudformation.amazonaws.com
            Action: sts:AssumeRole
      Path: "/"
      Policies:
        - PolicyName: ResourceTypePolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - "fsx:DescribeFileSystems"
                  - "lambda:InvokeFunction"
                  - "secretsmanager:GetSecretValue"
                Resource: "*"
Outputs:
  ExecutionRoleArn:
    Value:
      Fn::GetAtt: ExecutionRole.Arn
```
You can use the above template to create the role by running the following command:
```
aws cloudformation create-stack --stack-name CreateExecutionRoleForNetAppCFextensions --template-body file://<path-to-template> --capabilities CAPABILITY_NAMED_IAM
```

### Step 2: Activate the Extensions
The next step is to activate all the extension. You can do that by running the `activate_extensions`
script found in the `scripts` directory in this repository.
```
./activate_extensions -r <aws-region> -p <preview-key> -a <role-arn>
```
Where:
- `<aws-region>` is the AWS region you want to activate the extensions in.
- `<preview-key>` is the preview key you obtained from NetApp.
- `<role-arn>` is the ARN of the role that the extensions will assume to create resources.

### Step 3: Deploy a Workload Factory Link
Before you can use any of the FSxN extensions you must have a Workload Factory Link deployed.
If you don't already have one, you can either deploy one via the [Workload Factory console](https://console.workloads.netapp.com),
or you can create one by using the `NetApp::FSxN::Link::MODULE` CloudFormation module, which is part of the third party extensions.
To make deploying the Workload Factory Link easy you can use the `deploy_link` script found in the `scripts` directory in this repository.
It invokes the `NetApp::FSxN::Link::Module` module with the appropriate parameters and will output the ARN
of the Workload Factory Link Lambda function that will be used in all of the CloudFormation templates that use these FSxN extensions.

Here is the synopsis of how to use the `deploy_link` script:
```
./deploy_link -r <aws-region> -s <subnet-id>,<subnet-id> -g <security-group-id>,<security-group-id> -n <link_name>
```
Where:
- `<aws-region>` is the AWS region you want to activate the extensions in.
- `<subnet-id>,<subnet-id>` are the subnet(s) you want to deploy the link in. No spaces between the subnet IDs.
Only one is required, but is recommended to have at least two. These subnets must have access to the FSxN management endpoint.
- `<security-group-id>,<security-group-id>` are the security group(s) that will be attached to the Lambda Link function.
The security groups must allow access to the FSxN management endpoint over port 443.
No spaces between the security group IDs. Only one is required.
- `<link_name>` is the name you want to give the link. It is also used as the name assigned to the link Lambda function.

### Step 4: Create an AWS Secret Manager Secret
All of the extensions use an AWS Secrets Manager secret to obtain the credentials needed to manage the FSx for ONTAP file system.
The secret should be a JSON object with the one key. The key can be named anything, but the value should be of the form `"username:password"`.
This allows you to use any username you want. If you want to use fsxadmin (the default admin for an FSx for ONTAP file system), then the value can be just that user's password.

The following command can be used to create a secret:
```
aws secretsmanager create-secret --name <secret-name> --secret-string '{"<key-name>":"<username>:<password>"}'
```
Where:
```
<secret-name> is the name you want to give the secret.
<key-name> is the name of the key in the secret. It can be anything you want.
<username> is the username you want to use to manage the FSx for ONTAP file system.
<password> is the password for the username.
```

## Sample CloudFormation Templates
Once you have done the above steps you are ready to start using the examples in this repository.

| File | Description |
|------|-------------|
|create_clone.yaml|Creates a clone of an existing FSx for NetApp ONTAP volume.|
|create_export.yaml|Creates an export policy for an FSx for NetApp ONTAP file system.|
|create_sm_with_peering.yaml|Creates a SnapMirror relationship with a specified source volume. It will also establish the vserver and cluster peering relationships.|
|create_sm_without_peering.yaml|Creates a SnapMirror relationship with a specified source volume. It assumes that there is already a peering relationship between the source and destination clusters and vservers.|
|create_snapshot.yaml|Creates a snapshot of an FSx for NetApp ONTAP volume.|
|create_volume.yaml|Creates an FSx for NetApp ONTAP volume.|

Note that there is a script, in the `scripts` directory, for each of these CloudFormation templates that can be used to deploy them via the AWS CLI.

## Author Information

This repository is maintained by the contributors listed on [GitHub](https://github.com/NetApp/FSx-ONTAP-samples-scripts/graphs/contributors).

## License

Licensed under the Apache License, Version 2.0 (the "License").

You may obtain a copy of the License at [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an _"AS IS"_ basis, without WARRANTIES or conditions of any kind, either express or implied.

See the License for the specific language governing permissions and limitations under the License.

© 2025 NetApp, Inc. All Rights Reserved.
