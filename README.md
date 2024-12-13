# FSx-ONTAP-samples-scripts

FSx for NetApp ONTAP is an AWS service providing a comprehensive set of advanced storage features purposely
built to maximize cost performance, resilience, and accessibility in business-critical workloads.

## Overview

This GitHub repository contains comprehensive code samples and automation scripts for FSx for Netapp ONTAP operations,
promoting the use of Infrastructure as Code (IAC) tools and encouraging developers to extend the product's
functionalities through code. The samples here go alongside the automation, management and monitoring that
[BlueXP Workload Factory](https://console.workloads.netapp.com) provides.

We welcome contributions from the community! Please read our [contribution guidelines](CONTRIBUTING.md) before getting started.

Have a great idea? We'd love to hear it! Please email us at [ng-fsxn-github-samples@netapp.com](mailto:ng-fsxn-github-samples@netapp.com).

## Table of Contents

* [AI](/AI)
    * [GenAI ChatBot application sample](/AI/GenAI-ChatBot-application-sample)
* [Anisble](/Ansible)
    * [FSx ONTAP inventory report](/Ansible/fsx_inventory_report)
    * [SnapMirror report](/Ansible/snapmirror_report)
* [CloudFormation](/CloudFormation)
    * [Deploy FSx for ONTAP](/CloudFormation/deploy-fsx-ontap)
* [EKS](/EKS)
    * [FSx for ONTAP as persistent storage for EKS](/EKS/FSxN-as-PVC-for-EKS)
* [Management Utilities](/Management-Utilities)
    * [Auto Create SnapMirror Relationships](/Management-Utilities/auto_create_sm_relationships)
    * [Auto Rotate Secrets Manager Secret and FSxN Password](/Management-Utilities/fsxn-rotate-secret)
    * [Auto Set FSxN Auto Volume Grow](/Management-Utilities/auto_set_fsxn_auto_grow)
    * [AWS CLI management scripts for FSx ONTAP](/Management-Utilities/fsx-ontap-aws-cli-scripts)
    * [FSx for ONTAP iscsi volume creation for Windows](/Management-Utilities/iscsi-vol-create-and-mount)
    * [Warm Performance Tier](/Management-Utilities/warm_performance_tier)
* [Monitoring](/Monitoring)
    * [Automatically Add CloudWatch Alarms for FSx Resources](/Monitoring/auto-add-cw-alarms)
    * [CloudWatch Dashboard for FSx for ONTAP](/Monitoring/CloudWatch-FSx)
    * [Ingest FSx ONTAP NAS audit logs into CloudWatch](/Monitoring/ingest_nas_audit_logs_into_cloudwatch)
    * [LUN Monitoring CloudWatch Dashboard](/Monitoring/LUN-monitoring)
    * [Monitor and alert on FSx for ONTAP Services with Lambda](/Monitoring/monitor-ontap-services)
    * [Monitor FSx for ONTAP with Harvest on EKS](/Monitoring/monitor_fsxn_with_harvest_on_eks)
* [Solutions](/Solutions)
    * [K8s applications non-stdout logs collection into ELK](/Solutions/EKS-logs-to-ELK)
* [Terraform](/Terraform)
    * [Deployment of FSx ONTAP with VPN for File Share Access](/Terraform/deploy-fsx-ontap-fileshare-access)
    * [Deployment of SQL Server on EC2 with FSx ONTAP](/Terraform/deploy-fsx-ontap-sqlserver)
    * [FSx ONTAP deployment using Terraform](/Terraform/deploy-fsx-ontap)
    * [FSx ONTAP Replication](/Terraform/fsxn-replicate)

## Author Information

This repository is maintained by the contributors listed on [GitHub](https://github.com/NetApp/FSx-ONTAP-samples-scripts/graphs/contributors).

## License

Licensed under the Apache License, Version 2.0 (the "License").

You may obtain a copy of the License at [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License
is distributed on an _"AS IS"_ basis, without WARRANTIES or conditions of any kind, either express or implied.

See the License for the specific language governing permissions and limitations under the License.

© 2024 NetApp, Inc. All Rights Reserved.
