# Support Scripts

## Description
This folder mostly contains scripts that can be used to drive the CloudFormation templates in the folder above.
There are also a couple scripts that can be used to help enable the NetApp FSxN CloudFormation extensions.

| Script | Description |
| ------ | ----------- |
|create_SM_relationship| This script will deploy a CloudFormation stack that creates a SnapMirror relationship between two volumes. Can be be used with both the create_sm_with_peering.yaml create_sm_without_peering.yaml CloudFormation templates. |
|create_clone| This script will deploy a CloudFormation stack that creates a clone of a volume. It is designed to be used with the create_clone.yaml CloudFormation template|
|create_export_policy| This script will deploy a CloudFormation stack that creates an export policy. It is designed to be used with the create_export_policy.yaml CloudFormation template|
|create_snapshot| This script will deploy a CloudFormation stack that creates a snapshot of a volume. It is designed to be used with the create_snapshot.yaml CloudFormation template|
|create_volume| This script will deploy a CloudFormation stack that creates a FSx for ONTAP volume. It is designed to be used with the create_volume.yaml CloudFormation template |
|activate_extensions| This script will activate all the NetApp FSxN CloudFormation extensions in the AWS account for a specific region.|
|deactivate_extensions | This script will deactivate all the NetApp FSxN CloudFormation extensions in the AWS account for a specific region.|
|deploy_link | This script will use CloudFormation to deploy a Workload Factory Link.|
|createClone.py | This is a Python script that will create a clone of a volume using boto to deploy a CloudFormation stack that creates a clone.|

## Usage
To run these scripts you'll need to download them, change the permissions to be executable, and then run them. For example:
```bash
chmod +x create_volume
./create_volme -r us-west-2 -l arn:aws:lambda:ca-central-1:759999999999:function:wf-link -s arn:aws:secretsmanager:us-east-1:759999999999:secret:fsnSecret-yyaL32 -f fs-02a89999999999999 -v prod -n vol1 -t ../create_volume.yaml
```

To see the required parameters for each script, you can run the script with the `-h` flag. For example:
```bash
./create_volume -h
Usage: create_volume [-r region] -l link_ARN -s secret_ARN [-k secret_key] -f fsx_id -v svm_name -n volune_name [-z size_in_MB] [-a aggregate] -t template
Notes:
  The default region is the region configured in the AWS CLI.
  The default secret key is 'credentials'.
  The default aggregate is "aggr1".
  The default size is 20MB.
```

## Author Information

This repository is maintained by the contributors listed on [GitHub](https://github.com/NetApp/FSx-ONTAP-samples-scripts/graphs/contributors).

## License

Licensed under the Apache License, Version 2.0 (the "License").

You may obtain a copy of the License at [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an _"AS IS"_ basis, without WARRANTIES or conditions of any kind, either express or implied.

See the License for the specific language governing permissions and limitations under the License.

© 2025 NetApp, Inc. All Rights Reserved.
