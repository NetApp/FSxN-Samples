# Deploy an SQL Server on EC2 with Amazon FSx for NetApp ONTAP

The sample terraform deployment will create a Single-AZ Amazon FSx for NetApp ONTAP filesystem, create two LUN's on FSxN volume, deploy EC2 instance with SQL Server 2022 Standard and attach the FSxN LUN's as **SQL Data** and **SQL Log** volumes.

## Table of Contents

- [Introduction](#introduction)
- [Repository Overview](#repository-overview)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Author Information](#author-information)
- [License](#license)

## Introduction

### Repository Overview

This repository is meant for deployment of SQL Server on EC2 with FSxN. The following files and modules are part of this deployment.

#### Terraform Files

| File          | File Path                                | Description                                                                                                                                                                             |
| ------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| main.tf       | deploy-fsx-ontap-sqlserver/main.tf       | This is the primary terraform file that contains provider information and module configuration for SQL Server EC2 and Amazon FSx for NetApp ONTAP                                       |
| networking.tf | deploy-fsx-ontap-sqlserver/networking.tf | Creates the networking components - VPC, Public and Private Subnets, Internet Gateway, NAT Gateway, Route Table (private and public), Security Groups (default, EC2 to FSxN and others) |
| ssm.tf        | deploy-fsx-ontap-sqlserver/ssm.tf        | Creates an SSM parameter to store the password for the file system                                                                                                                      |
| variables.tf  | deploy-fsx-ontap-sqlserver/variables.tf  | Defines all the variables (and default values) used in main.tf, networking.tf, ssm.tf                                                                                                   |

#### Terraform Modules

| Module | File          | File Path                                             | Description                                                                                                                                                                             |
| ------ | ------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ec2    | ec2-ami.tf    | deploy-fsx-ontap-sqlserver/modules/ec2/ec2-ami.tf     | This is the primary terraform file that contains provider information and module configuration for SQL Server EC2 and Amazon FSx for NetApp ONTAP                                       |
| ec2    | ec2-sql.tf    | deploy-fsx-ontap-sqlserver/modules/ec2/ec2-sql.tf     | Creates the networking components - VPC, Public and Private Subnets, Internet Gateway, NAT Gateway, Route Table (private and public), Security Groups (default, EC2 to FSxN and others) |
| ec2    | variables.tf  | deploy-fsx-ontap-sqlserver/modules/ec2/variables.tf   | Defines all the variables (and default values) used in main.tf, networking.tf, ssm.tf                                                                                                   |
| ec2    | outputs.tf    | deploy-fsx-ontap-sqlserver/modules/ec2/outputs.tf     | Defines the output variables for SQL Server                                                                                                                                             |
| fsxn   | fsx-fs.tf     | deploy-fsx-ontap-sqlserver/modules/fsxn/fsx-fs.tf     | Defines the Amazon FSx for NetApp ONTAP file system and it's properties (SSD, Throughput, Deployment Mode etc.)                                                                         |
| fsxn   | fsx-svm.tf    | deploy-fsx-ontap-sqlserver/modules/fsxn/fsx-svm.tf    | Defines the Storage Virtual Machine (SVM) to be created in the file system                                                                                                              |
| fsxn   | fsx-volume.tf | deploy-fsx-ontap-sqlserver/modules/fsxn/fsx-volume.tf | Defines the SQL Data and SQL Log volumes to be created in the file system under the SVM                                                                                                 |
| fsxn   | outputs.tf    | deploy-fsx-ontap-sqlserver/modules/fsxn/outputs.tf    | Defines the output variables that are used further downstream in the deployment                                                                                                         |
| fsxn   | variables.tf  | deploy-fsx-ontap-sqlserver/modules/fsxn/variables.tf  | Defines all the variables (and default values) used in fsx-fs.tf, fsx-svm.tf, fsx-volume, outputs.tf, variables.tf                                                                      |

### Providers

| Name                                                                     | Version  |
| ------------------------------------------------------------------------ | -------- |
| <a name="requirement_terraform"></a> [terraform](#requirement_terraform) | >= 1.6.6 |
| <a name="requirement_aws"></a> [aws](#requirement_aws)                   | >= 5.25  |

### Inputs

| Name                  | Description                                                                                                   | Type           | Default                              | Required |
| --------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- | ------------------------------------ | :------: |
| creator_tag           | Creator Tag assigned for all the resources created                                                            | `string`       |                                      |   Yes    |
| environment           | Name of the environment (demo, test, qa etc.)                                                                 | `string`       | `Demo`                               |    No    |
| aws_location          | AWS region                                                                                                    | `string`       | `ap-southeast-1`                     |   Yes    |
| availability_zones    | Availability Zones corresponding to the regions                                                               | `list(string)` | `"ap-southeast-1", "ap-southeast-2"` |   Yes    |
| ec2_instance_type     | SQL Server EC2 instance type                                                                                  | `string`       | `t3.2xlarge`                         |   Yes    |
| ec2_instance_keypair  | EC2 Key Pair to be assigned for the deployed EC2 instance                                                     | `string`       |                                      |   Yes    |
| ec2_iam_role          | IAM Role assigned to the EC2 (see section)[#create-an-iam-role-and-attach-the-policy-amazonssmreadonlyaccess] | `string`       |                                      |   Yes    |
| fsxn_password         | Password for the fsxadmin user assigned to the filesystem                                                     | `string`       |                                      |   Yes    |
| volume_security_style | Root Volume and Flex Volume Security Style                                                                    | `string`       | `NTFS`                               |   Yes    |
| vpc_cidr              | CIDR Range for the VPC to be created                                                                          | `string`       | `10.0.0.0/16`                        |   Yes    |
| public_subnets_cidr   | 2 x Public Subnets to be created in the VPC                                                                   | `list(string)` | `"10.0.0.0/20", "10.0.16.0/20"`      |   Yes    |
| private_subnets_cidr  | 2 x Private Subnets to be created in the VPC                                                                  | `list(string)` | `"10.0.128.0/20", "10.0.144.0/20"`   |   Yes    |

### Outputs

| Name                     | Description                              |
| ------------------------ | ---------------------------------------- |
| FSxN_management_ip       | FSxN File System Management Endpoint     |
| FSxN_svm_iscsi_endpoints | FSxN SVM iSCSI IP addresses              |
| FSxN_sql_server_ip       | SQL Server EC2 IP addresses              |
| FSxN_file_system_id      | FSxN File System Id                      |
| FSxN_svm_id              | FSxN Storage Virtual Machine Id          |
| FSxN_sql_data_volume     | FSxN SQL Data Volume Id and Name         |
| FSxN_sql_log_volume      | FSxN SQL Log Volume Id and Name          |
| instance_id              | SQL Server Instance Id                   |
| public_ip                | SQL Server Public IP                     |
| private_ip               | SQL Server Private IP                    |
| hostname                 | SQL Server Hostname                      |
| username                 | SQL Server WIndows Admin User            |
| password                 | SQL Server Windows Admin USer's Password |

### What to expect

The terraform deployment creates the following components:

- VPC with 2 Public and 2 Private Subnets
- Route Tables - Public and Private
- Internet Gateway
- NAT Gateway
- Security Groups for the File System and EC2
- Amazon FSx for NetApp ONTAP file system with 1 SVM and 2 Volumes for SQL Data and Log
- EC2 Instance with SQL Server (see [EC2 Configuration section for more details](#EC2Configuration))

#### EC2 Configuration

Following are the configuration steps when the EC2 is deployed:

- Starts the iSCSI Service
- Install Nuget Provider for Powershell
- Install DBATools Powershell Module
- Install NetApp.ONTAP Powershell Module
- Install MPIO (Multipath IO) _(**Note:** EC2 restarts automatically after installation and configuration continues)_
- Checks for LUNS and Disks _(if already created and formatted then script exists)_
- Configures the FSxN Volumes _(refer to Best Practices in the [TR-4923: SQL Server on AWS EC2 using Amazon FSx for NetApp ONTAP](https://docs.netapp.com/us-en/netapp-solutions/databases/sql-aws-ec2.html))_
- Create LUNs for SQL Data and SQL Log
- Create iGroup and map the luns and iSCSI initiator address of the server
- Establish iSCSI connectivity
- Format the Disks
- Set the Default Data and Log drives in SQL Server
- Restart the SQL Server service
- Install a Sample Database _(**Optional:** if you do not wish to install the database set the parameter sql_install_sample_database to false in main.tf under module "sqlserver")_

> [!NOTE]
> The EC2 Configuration can take about 10 mins and may vary depending on the instance type selected.

> [!TIP]
> To check the progress of the configuration, login to the EC2 instance and navigate to the directory `C:\Windows\System32\config\systemprofile\AppData\Local\Temp\` in the windows explorer
> Browse the folders in the directory with the prefix `EC2Launchxxxxxxxxx`.
> The folder contains output.tmp and err.tmp files that will provide more information about the configuration progress or if there are any errors during the configuration process.

## Prerequisites

1. [Terraform prerequisites](#terraform)
2. [AWS prerequisites](#aws-account-setup)

### Terraform

| Name                                                                     | Version  |
| ------------------------------------------------------------------------ | -------- |
| <a name="requirement_terraform"></a> [terraform](#requirement_terraform) | >= 1.6.6 |
| <a name="requirement_aws"></a> [aws](#requirement_aws)                   | >= 5.25  |

### AWS Account Setup

- You must have an AWS Account with necessary permissions to create and manage resources
- Configure your AWS Credentials on the server running this Terraform module. This can be derived from several sources, which are applied in the following order:

  1. Parameters in the provider configuration
  2. Environment variables
  3. Shared credentials files
  4. Shared configuration files
  5. Container credentials
  6. Instance profile credentials and Region

  This order matches the precedence used by the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) and the [AWS SDKs](https://aws.amazon.com/tools/).

> [!NOTE]
> In this sample, the AWS Credentials were configured through [AWS CLI](https://aws.amazon.com/cli/), which adds them to a shared configuration file (option 4 above). Therefore, this documentation only provides guidance on setting-up the AWS credentials with shared configuration file using AWS CLI.

---

#### Configure AWS Credentials using AWS CLI

The AWS Provider can source credentials and other settings from the shared configuration and credentials files. By default, these files are located at `$HOME/.aws/config` and `$HOME/.aws/credentials` on Linux and macOS, and `"%USERPROFILE%\.aws\credentials"` on Windows.

There are several ways to set your credentials and configuration setting using AWS CLI. We will use [`aws configure`](https://docs.aws.amazon.com/cli/latest/reference/configure/index.html) command:

Run the following command to quickly set and view your credentails, region, and output format. The following example shows sample values:

```shell
 $ aws configure
 AWS Access Key ID [None]: < YOUR-ACCESS-KEY-ID >
 AWS Secret Access Key [None]: < YOUR-SECRET-ACCESS-KE >
 Default region name [None]: < YOUR-PREFERRED-REGION >
 Default output format [None]: json
```

To list configuration data, use the [`aws configire list`](https://docs.aws.amazon.com/cli/latest/reference/configure/list.html) command. This command lists the profile, access key, secret key, and region configuration information used for the specified profile. For each configuration item, it shows the value, where the configuration value was retrieved, and the configuration variable name.

---

#### Create an IAM Role and attach the policy "AmazonSSMReadOnlyAccess"

1. **Navigate to the IAM Service**:

   - In the AWS Management Console, search for "IAM" or find it under "Security, Identity, & Compliance" in the services menu.

2. **Create a New IAM Role**:

   - In the IAM dashboard, click on "Roles" in the left navigation pane.
   - Click the "Create role" button.

3. **Select the Service that Will Use the Role**:

   - Under "Select type of trusted entity", choose "AWS service" since you want this role to be used by an AWS service.
   - Under "Choose a use case", select "EC2".

4. **Attach Permissions Policies**:

   - Search for "AmazonSSMReadOnlyAccess" in the policy search box.
   - Select the checkbox next to "AmazonSSMReadOnlyAccess".

5. **Review Role Details**:

   - Click "Next: Tags" to skip adding tags (optional).
   - Click "Next: Review" to review the role details.

6. **Name the Role**:

   - Enter a name for your role in the "Role name" field (e.g., `SSMReadOnlyRole`).
   - Optionally, add a description for the role.

7. **Create the Role**:
   - Click the "Create role" button.

> [!NOTE]
> The role is required to fetch the password for fsxadmin from SSM Secured Parameters. Terraform creates an SSM Paramter which is retrieved via the powershell script of EC2 instance. The role allows the retrieval of the parameter and execute the necessary operations on the filesystem.
> Alternatively, the password can also be entered in the `user_data` section under `$ssmPass` variable found in the ec2-sql.tf file (not recommended).

## Usage

#### 1. Clone the repository

In your server's terminal, navigate to the location where you wish to store this Terraform repository, and clone the repository using your preferred authentication type. In this example we are using HTTPS clone:

```shell
git clone -b strigo-lab-sqlserver https://github.com/NetApp/FSx-ONTAP-samples-scripts
```

#### 2. Navigate to the directory

```shell
cd deploy-fsx-ontap-sqlserver
```

#### 3. Initialize Terraform

This directory represents a standalone Terraform module. Run the following command to initialize the module and install all dependencies:

```shell
terraform init
```

A succesfull initialization should display the following output:

```shell

Initializing the backend...
Initializing modules...

Initializing provider plugins...
- Reusing previous version of hashicorp/local from the dependency lock file
- Reusing previous version of hashicorp/aws from the dependency lock file
- Using previously-installed hashicorp/local v2.5.1
- Using previously-installed hashicorp/aws v5.25.0

Terraform has been successfully initialized!

You may now begin working with Terraform. Try running "terraform plan" to see
any changes that are required for your infrastructure. All Terraform commands
should now work.

If you ever set or change modules or backend configuration for Terraform,
rerun this command to reinitialize your working directory. If you forget, other
commands will detect it and remind you to do so if necessary.

```

You can see that Terraform recognizes the modules required by our configuration: `hashicorp/aws`.

#### 4. Create Variables Values

- Copy or Rename the file **`terraform.sample.tfvars`** to **`terraform.tfvars`**

- Open the **`terraform.tfvars`** file in your preferred text editor. Update the values of the variables to match your preferences and save the file. This will ensure that the Terraform code deploys resources according to your specifications.

- Set the parameters in terraform.tfvars

  ##### Sample file

  ***

  ```ini
    creator_tag           = "<Creator Tag>"
    environment           = "Demo"
    aws_location          = "<AWS Region>"
    availability_zones    = ["<Availability Zone 1>", "<Availability Zone 2>"]
    ec2_instance_type     = "t3.2xlarge"
    ec2_instance_keypair  = "<EC2 Instance Key Pair>"
    ec2_iam_role          = "<IAM Role>"
    fsxn_password         = "<Password for fsxadmin>"
    volume_security_style = "NTFS"
    vpc_cidr              = "10.0.0.0/16"
    public_subnets_cidr   = ["10.0.0.0/20", "10.0.16.0/20"]
    private_subnets_cidr  = ["10.0.128.0/20", "10.0.144.0/20"]
  ```

> [!IMPORTANT] > **Make sure to replace the values with ones that match your AWS environment and needs.**

#### 5. Create a Terraform plan

Run the following command to create an execution plan, which lets you preview the changes that Terraform plans to make to your infrastructure:

```shell
terraform plan
```

Ensure that the proposed changes match what you expected before you apply the changes!

#### 6. Apply the Terraform plan

Run the following command to execute the Terrafom code and apply the changes proposed in the `plan` step:

```shell
terraform apply
```

## Author Information

This repository is maintained by the contributors listed on [GitHub](https://github.com/NetApp/FSx-ONTAP-samples-scripts/graphs/contributors).

## License

Licensed under the Apache License, Version 2.0 (the "License").

You may obtain a copy of the License at [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an _"AS IS"_ basis, without WARRANTIES or conditions of any kind, either express or implied.

See the License for the specific language governing permissions and limitations under the License.

<!-- END_TF_DOCS -->

> [!IMPORTANT]
> This sample deployment is not meant for production use.

© 2024 NetApp, Inc. All Rights Reserved.
