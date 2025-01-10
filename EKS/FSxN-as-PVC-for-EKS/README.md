# FSx for NetApp ONTAP as persistent storage

## Table of Contents
* [Introduction](#introduction)
* [Installation Overview](#Installation-Overview)
* [Detailed Instructions](#Detailed-instructions)
  * [Clone the "NetApp/FSx-ONTAP-samples-scripts" repo from GitHub](#Clone-the-NetAppFSx-ONTAP-samples-scripts-repo-from-GitHub)
  * [Make any desired changes to the variables.tf file](#Make-any-desired-changes-to-the-variablestf-file)
  * [Initialize the Terraform environment](#Initialize-the-Terraform-environment)
  * [Deploy the resources](#Deploy-the-resources)
  * [SSH to the jump server to complete the setup](#SSH-to-the-jump-server-to-complete-the-setup)
  * [Configure the 'aws' CLI](#Configure-the-aws-CLI)
  * [Allow access to the EKS cluster for your user id](#Allow-access-to-the-EKS-cluster-for-your-user-id)
  * [Configure kubectl to use the EKS cluster](#Configure-kubectl-to-use-the-EKS-cluster)
  * [Confirm Astra Trident is up and running](#Confirm-Astra-Trident-is-up-and-running)
  * [Configure the Trident CSI backend to use FSx for NetApp ONTAP](#Configure-the-Trident-CSI-backend-to-use-FSx-for-NetApp-ONTAP)
  * [Create a Kubernetes storage class](#Create-a-Kubernetes-storage-class)
* [Create a stateful application](#Create-a-stateful-application)
  * [Create a Persistent Volume Claim](#Create-a-Persistent-Volume-Claim)
  * [Deploy a MySQL database using the PVC](#Deploy-a-MySQL-database-using-the-storage-created-above)
  * [Populate the MySQL database with data](#Populate-the-MySQL-database-with-data)
* [Create a snapshot of the MySQL data](#Create-a-snapshot-of-the-MySQL-data)
  * [Install the Kubernetes Snapshot CRDs and Snapshot Controller](#Install-the-Kubernetes-Snapshot-CRDs-and-Snapshot-Controller)
  * [Create a snapshot class based on the CRD instsalled](#Create-a-snapshot-class-based-on-the-CRD-installed)
  * [Create a snapshot of the MySQL data](#Create-a-snapshot-of-the-MySQL-data)
* [Clone the MySQL data to a new persistent volume](#Clone-the-MySQL-data-to-a-new-persistent-volume)
  * [Create a new MySQL database using the cloned volume](#Create-a-new-MySQL-database-using-the-cloned-volume)
  * [Confirm that the new database is up and running](#Confirm-that-the-new-database-is-up-and-running)
* [Final steps](#Final-steps)
* [Author Information](#author-information)
* [License](#license)

## Introduction

In this sample you'll find the instructions, and the code, necessary to deploy an AWS EKS
cluster with an Amazon FSx for NetApp ONTAP File System (FSxN) to provide persistent storage
for it. It will leverage NetApp's Astra Trident to provide the interface between EKS to FSxN.

## Prerequisites

A Unix based system with the following installed:
- HashiCorp's Terraform
- AWS CLI, authenticated with an account that has privileges necessary to:
	- Deploy an EKS cluster
	- Deploy an FSx for Netapp ONTAP File System
	- Create security groups
  - Create policies and roles
  - Create secrets in AWS SecretsManager
  - Create a VPC and subnets
  - Create a NAT Gateway
  - Create a Internet Gateway
  - Create an EC2 instance

## Installation Overview
The overall process is as follows:
- Ensure the prerequisites have been installed and configured.
- Clone this repo from GitHub.
- Make changes to the variables.tf file. Only one change is really required.
- Run 'terraform init' to initialize the terraform environment.
- Run 'terraform apply -auto-approve' to:
  - Create a new VPC with public and private subnets.
  - Deploy a FSx for NetApp ONTAP File System.
  - Create a secret in AWS SecretsManager to hold the FSxN password.
  - Deploy an EKS cluster.
  - Deploy an EC2 Linux based instance. Used as a jump server to complete the setup.
  - Create policies, roles and security groups to protect the new environment.
- SSH to the Linux based instance to complete the setup:
  - Install the FSx for NetApp ONTAP Trident CSI driver.
  - Configure the Trident CSI driver.
  - Create a Kubernetes storage class.
- Deploy a sample application to test the storage with.

## Detailed Instructions
### Clone the "NetApp/FSx-ONTAP-samples-scripts" repo from GitHub
Run the following commands to clone the repo and change into the directory where the
terraform files are located:
```bash
git clone https://github.com/NetApp/FSx-ONTAP-samples-scripts.git
cd FSx-ONTAP-samples-scripts/EKS/FSxN-as-PVC-for-EKS/terraform
```
### Make any desired changes to the variables.tf file.
Variables that can be changed include:
- aws_region - The AWS region where you want to deploy the resources.
- aws_secrets_region - The region where the fsx password secret will be created.
- fsx_name - The name you want applied to the FSx for NetApp ONTAP File System. Must not already exist.
- secret_name_prefix - The base name of the AWS SecretsManager secrets that will be created that will hold the FSxN adminstrator, and SVM, passwords.
A random string will be appended to this name to ensure uniqueness.
- fsx_storage_capacity - The storage capacity of the FSx for NetApp ONTAP File System.
Read the "description" of the variable to see the valid range.
- fsx_throughput_capacity - The throughput capacity of the FSx for NetApp ONTAP File System.
Read the "description" of the variable to see valid values.
- key_pair_name - The name of the EC2 key pair to use to access the jump server.
- secure_ips - The IP address ranges to allow SSH access to the jump server. The default is wide open.

:warning: **NOTE:** You must change the key_pair_name variable, otherwise the deployment will not complete succesfully.
### Initialize the Terraform environment
Run the following command to initialize the terraform environment.
```bash
terraform init
```

### Deploy the resources
Run the following command to deploy all the resources:
```bash
terraform apply --auto-approve
```
There will be a lot of output, and it will take 20 to 40 minutes to complete. Once done,
the following is an example of last part of the output of a successful deployment:
```bash
Outputs:

eks-cluster-name = "eksfs-eks-lutuycvJ"
eks-jump-server = "Instance ID: i-00de97f46e3c9a617, Public IP: 54.213.93.236"
fsx-id = "fs-04f1b48f8da639a7f"
fsx-management-ip = "198.19.255.245"
fsx-password-secret-arn = "arn:aws:secretsmanager:us-west-2:759995470648:secret:keith-eksfs-fsxn-55fd4eb7-4Oy2ab"
fsx-password-secret-name = "eksfs-fsxn-55fd4eb7"
fsx-svm-name = "ekssvm"
region = "us-west-2"
svm-password-secret-arn = "arn:aws:secretsmanager:us-west-2:759995470648:secret:keith-eksfs-svm-6ad11609-nApoUp"
svm-password-secret-name = "eksfs-svm-6ad11609"
vpc-id = "vpc-0791cc0566462082b"
```
:bulb: **Tip:** You will use the values in the commands below, so probably a good idea to copy the output somewhere
so you can easily reference it later.

### SSH to the jump server to complete the setup
Use the following command to 'ssh' to the jump server:
```bash
ssh -i <path_to_key_pair> ubuntu@<jump_server_public_ip>
```
Where:
- <path_to_key_pair> is the file path to where you have stored the key_pair that you
referenced in the variables.tf file.
- <jump_server_public_ip> is the IP address of the jump server that was displayed
in the output from the `terraform apply` command.

### Configure the 'aws' CLI
There are various ways to configure the AWS cli. If you are unsure how to do it, please
refer to this the AWS documentation for instructions:
[Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)

### Allow access to the EKS cluster for your user id
AWS's EKS clusters have a secondary form for permissions. As such, you have to add an "access-entry"
to your EKS configuration and associate it with the Cluster Admin policy to be able to view and
configure the EKS cluster. The first step to do this is to find out your IAM ARN.
You can do that via this command:
```bash
user_ARN=$(aws sts get-caller-identity --query Arn --output text)
echo $user_ARN
```
Note that if you are using an SSO to authenticate with AWS, then the actual username
you need to add is slightly different than what is output from the above command.
The following command will take the output from the above command and format it correctly:

:warning: **Caution:** Only run this command if you are using an SSO to authenticate with aws.
```bash
user_ARN=$(aws sts get-caller-identity | jq -r '.Arn' | awk -F: '{split($6, parts, "/"); printf "arn:aws:iam::%s:role/aws-reserved/sso.amazonaws.com/%s\n", $5, parts[2]}')
echo $user_ARN
```
The above command will leverage a standard AWS role that is created when configuring AWS to use an SSO.

As you can see above, a variable named "user_ARN" was create to hold the your user's ARN. To make
the next few commands easy, also create variables that hold the AWS region and EKS cluster name.
```bash
aws_region=<AWS_REGION>
cluster_name=<EKS_CLUSTER_NAME>
```
Of course, replace <AWS_REGION> with the region where the resources were deployed. And replace
<EKS_CLUSTER_NAME> with the name of your EKS cluster. Both of these values can be found
from the output of the `terraform apply` command.

Once you have your variables set, add the EKS access-entry by running these commands:
```bash
aws eks create-access-entry --cluster-name $cluster_name --principal-arn $user_ARN --region $aws_region
aws eks associate-access-policy --cluster-name $cluster_name --principal-arn $user_ARN --region $aws_region --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy --access-scope type=cluster
```

### Configure kubectl to use the EKS cluster
AWS makes it easy to configure 'kubectl' to use the EKS cluster. You can do that by running this command:
```bash
aws eks update-kubeconfig --name $cluster_name --region $aws_region
```
Of course the above assumes the cluster_name and aws_region variables are still set from
running the commands above.

To confirm you can communicate with the EKS cluster run the following command:
```bash
kubectl get nodes
```
You should get output like this:
```bash
NAME                                       STATUS   ROLES    AGE   VERSION
ip-10-0-1-84.us-west-2.compute.internal    Ready    <none>   76m   v1.29.3-eks-ae9a62a
ip-10-0-2-117.us-west-2.compute.internal   Ready    <none>   76m   v1.29.3-eks-ae9a62a
```

### Confirm Astra Trident is up and running
Astra Trident should have been added to your EKS Cluster as part of the terraform deployment.
Confirm that it is up and running by running this command:
```bash
kubectl get pods -n trident
```
The output should look something like this:
```bash
NAME                                  READY   STATUS    RESTARTS   AGE
trident-controller-569f47fc59-hx2vn   6/6     Running   0          20h
trident-node-linux-pgcw9              2/2     Running   0          20h
trident-node-linux-zr8n7              2/2     Running   0          20h
trident-operator-67d6fd899b-jrnt2     1/1     Running   0          20h
```

### Configure the Trident CSI backend to use FSx for NetApp ONTAP
For the example below we are going to set up an NFS file system for a MySQL
database. To help facilitate that, we are going to set up Astra Trident as a backend provider.
Since we are going to be creating an NFS file system, we are going to use its `ontap-nas` driver.
Astra Trident has several different drivers to choose from. You can read more about the
different drivers it supports in the
[Astra Trident documentation.](https://docs.netapp.com/us-en/trident/trident-use/trident-fsx.html#fsx-for-ontap-driver-details)

:memo: **Note:** If you want to use an iSCSI LUN instead of an NFS file system, please refer to [these instructions](README-san.md).

In the commands below you're going to need the FSxN ID, the FSX SVM name, and the
secret ARN. All of that information can be obtained from the output
from the `terraform apply` command. If you have lost that output, you can always log back
into the server where you ran `terraform apply` and simply run it again. It should
state that there aren't any changes to be made and simply show the output again.

Note that a copy of this repo has been put into ubuntu's home directory on the
jump server for you. Don't be confused with this copy of the repo and the one you
used to create the environment with earlier. This copy will not have the terraform
state database, nor your changes to the variables.tf file, but it does have
other files you'll need to complete the setup.

After making the following substitutions in the commands below:
- \<fsx-id> with the FSxN ID.
- \<fsx-svm-name> with the name of the SVM that was created.
- \<secret-arn> with the ARN of the AWS SecretsManager secret that holds the SVM password (not the FSxN password).

Run them to configure Trident to use the FSxN file system that was
created earlier using the `terraform --apply` command:
```
cd ~/FSx-ONTAP-samples-scripts/EKS/FSxN-as-PVC-for-EKS
mkdir temp
export FSX_ID=<fsx-id>
export FSX_SVM_NAME=<fsx-svm-name>
export SECRET_ARN=<secret-arn>
envsubst < manifests/backend-tbc-ontap-nas.tmpl > temp/backend-tbc-ontap-nas.yaml
kubectl create -n trident -f temp/backend-tbc-ontap-nas.yaml
```
:bulb: **Tip:** Put the above commands in your favorite text editor and make the substitutions there. Then copy and paste the commands into the terminal.

To get more information regarding how the backed was configured, look at the
`temp/backend-tbc-ontap-nas.yaml` file.

To confirm that the backend has been appropriately configured, run this command:
```bash
kubectl get tridentbackendconfig -n trident
```
The output should look similar to this:
```bash
NAME                    BACKEND NAME            BACKEND UUID                           PHASE   STATUS
backend-fsx-ontap-nas   backend-fsx-ontap-nas   7a551921-997c-4c37-a1d1-f2f4c87fa629   Bound   Success
```
If the status is `Failed`, then you can add the "--output=json" option to the `kubectl get tridentbackendconfig`
command to get more information as to why it failed. Specifically, look at the "message" field in the output.
The following command will get just the status messages:
```bash
kubectl get tridentbackendconfig -n trident --output=json | jq '.items[] | .status.message'
```
Once you have resolved any issues, you can remove the failed backend by running:

:warning: **Caution:** Only run this command if the backend is in a failed state and you are ready to get rid of it.
```bash
kubectl delete -n trident -f temp/backend-tbc-ontap-nas.yaml
```
Now you can re-run the `kubectl create -n trident -f temp/backend-tbc-ontap-nas.yaml` command.
If the issue was with one of the variables that was substituted in, then you will need to
rerun the `envsubst` command to create a new `temp/backend-tbc-ontap-nas.yaml` file
before running the `kubectl create -n trident -f temp/backend-tbc-ontap-nas.yaml` command.

### Create a Kubernetes storage class
The next step is to create a Kubernetes storage class by executing:
```bash
kubectl create -f manifests/storageclass-fsxn-nas.yaml
```
To confirm it worked run this command:
```bash
kubectl get storageclass
```
The output should be similar to this:
```bash
NAME              PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
fsx-basic-nas     csi.trident.netapp.io   Delete          Immediate              true                   20h
gp2 (default)     kubernetes.io/aws-ebs   Delete          WaitForFirstConsumer   false                  44h
```
To see more details on how the storage class was defined, look at the `manifests/storageclass-fsxn-nas.yaml`
file.

## Create a stateful application
Now that you have set up Kubernetes to use Trident to interface with FSxN for persistent
storage, you are ready to create an application that will use it. In the example below,
we are setting up a MySQL database that will use an NFS file system provisioned on the
FSxN file system.

### Create a Persistent Volume Claim
The first step is to create an NFS file system for the database by running:

```bash
kubectl create -f manifests/pvc-fsxn-nas.yaml
```
To check that it worked, run:
```bash
kubectl get pvc
```
The output should look similar to this:
```bash
NAME               STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS    VOLUMEATTRIBUTESCLASS   AGE
mysql-volume-nas   Bound    pvc-1aae479e-4b27-4310-8bb2-71255134edf0   50Gi       RWO            fsx-basic-nas   <unset>                 114m
```
To see more details on how the PVC was defined, look at the `manifests/pvc-fsxn-nas.yaml` file.

If you want to see what was created on the FSxN file system, you can log into it and take a look.
You will want to login as the 'fsxadmin' user, using the password stored in the AWS SecretsManager secret.
You can find the IP address of the FSxN file system in the output from the `terraform apply` command, or
from the AWS console. Here is an example of logging in and listing all the volumes on the system:
```bash
ubuntu@ip-10-0-4-125:~/FSx-ONTAP-samples-scripts/EKS/FSxN-as-PVC-for-EKS$ ssh -l fsxadmin 198.19.255.174
(fsxadmin@198.19.255.174) Password:

FsxId0887a493c777c5122::> volume show
Vserver   Volume       Aggregate    State      Type       Size  Available Used%
--------- ------------ ------------ ---------- ---- ---------- ---------- -----
ekssvm    ekssvm_root  aggr1        online     RW          1GB    972.4MB    0%
ekssvm    trident_pvc_1aae479e_4b27_4310_8bb2_71255134edf0
                       aggr1        online     RW         50GB    50.00GB    0%
2 entries were displayed.

FsxId0887a493c777c5122::> quit
Goodbye
```

### Deploy a MySQL database using the storage created above
Now you can deploy a MySQL database by running:
```bash
kubectl create -f manifests/mysql-nas.yaml
```
To check that it is up run:
```bash
kubectl get pods
```
The output should look similar to this:
```bash
NAME                             READY   STATUS    RESTARTS   AGE
mysql-fsx-nas-79cdb57b58-m2lgr   1/1     Running   0          31s
```
Note that it might take a minute or two for the pod to get to the Running status.

To see how the MySQL was configured, check out the `manifests/mysql-nas.yaml` file.

### Populate the MySQL database with data

To confirm that the database can read and write to the persistent storage you need
to put some data in the database. Do that by first logging into the MySQL instance using the
command below. It will prompt for a password. In the yaml file used to create the database,
you'll see that we set that to `Netapp1!`
```bash
kubectl exec -it $(kubectl get pod -l "app=mysql-fsx-nas" --namespace=default -o jsonpath='{.items[0].metadata.name}') -- mysql -u root -p
```
After you have logged in, here is a session showing an example of creating a database, then creating a table, then inserting
some values into the table:
```
mysql> create database fsxdatabase; 
Query OK, 1 row affected (0.01 sec)

mysql> use fsxdatabase;
Database changed 

mysql> create table fsx (filesystem varchar(20), capacity varchar(20), region varchar(20));
Query OK, 0 rows affected (0.04 sec)

mysql> insert into fsx (`filesystem`, `capacity`, `region`) values ('netapp01','1024GB', 'us-east-1'),
('netapp02', '10240GB', 'us-east-2'),('eks001', '2048GB', 'us-west-1'),('eks002', '1024GB', 'us-west-2'),
('netapp03', '1024GB', 'us-east-1'),('netapp04', '1024GB', 'us-west-1'); 
Query OK, 6 rows affected (0.03 sec) 
Records: 6  Duplicates: 0  Warnings: 0
```

And, to confirm everything is there, here is an SQL statement to retrieve the data:
```
mysql> select * from fsx;
+------------+----------+-----------+
| filesystem | capacity | region    |
+------------+----------+-----------+
| netapp01   | 1024GB   | us-east-1 |
| netapp02   | 10240GB  | us-east-2 |
| eks001     | 2048GB   | us-west-1 |
| eks002     | 1024GB   | us-west-2 |
| netapp03   | 1024GB   | us-east-1 |
| netapp04   | 1024GB   | us-west-1 |
+------------+----------+-----------+
6 rows in set (0.00 sec)

mysql> quit
Bye
```

## Create a snapshot of the MySQL data
Of course, one of the benefits of FSxN is the ability to take space efficient snapshots of the volumes.
These snapshots take almost no additional space on the backend storage and pose no performance impact.

### Install the Kubernetes Snapshot CRDs and Snapshot Controller:
The first step is to install the Snapshot CRDs and the Snapshot Controller.
To do that by running these commands:
```bash
git clone https://github.com/kubernetes-csi/external-snapshotter 
cd external-snapshotter/ 
kubectl kustomize client/config/crd | kubectl create -f - 
kubectl -n kube-system kustomize deploy/kubernetes/snapshot-controller | kubectl create -f - 
kubectl kustomize deploy/kubernetes/csi-snapshotter | kubectl create -f - 
cd ..
```
### Create a snapshot class based on the CRD installed
Create a snapshot class by executing:
```bash
kubectl create -f manifests/volume-snapshot-class.yaml 
```
The output should look like:
```bash
volumesnapshotclass.snapshot.storage.k8s.io/fsx-snapclass created
```
To see how the snapshot class was defined, look at the `manifests/volume-snapshot-class.yaml` file.
### Create a snapshot of the MySQL data
Now that you have defined the snapshot class you can create a snapshot by running:
```bash
kubectl create -f manifests/volume-snapshot-nas.yaml
```
The output should look like:
```bash
volumesnapshot.snapshot.storage.k8s.io/mysql-volume-nas-snap-01 created
```
To confirm that the snapshot was created, run:
```bash
kubectl get volumesnapshot
```
The output should look like:
```bash
NAME                       READYTOUSE   SOURCEPVC          SOURCESNAPSHOTCONTENT   RESTORESIZE   SNAPSHOTCLASS   SNAPSHOTCONTENT                                    CREATIONTIME   AGE
mysql-volume-nas-snap-01   true         mysql-volume-nas                           63908Ki       fsx-snapclass   snapcontent-bdce9310-9698-4b37-9f9b-d1d802e44f17   2m18s          2m18s
```
To see more details on how the snapshot was defined, look at the `manifests/volume-snapshot-nas.yaml` file.

You can log onto the FSxN file system to see that the snapshot was created there:
```
FsxId0887a493c777c5122::> snapshot show -volume trident_pvc_*
                                                                 ---Blocks---
Vserver  Volume   Snapshot                                  Size Total% Used%
-------- -------- ------------------------------------- -------- ------ -----
ekssvm   trident_pvc_1aae479e_4b27_4310_8bb2_71255134edf0
                  snapshot-bdce9310-9698-4b37-9f9b-d1d802e44f17
                                                           140KB     0%    0%
```
## Clone the MySQL data to a new persistent volume
Now that you have a snapshot of the data, you can use it to create a read/write version
of it. This can be used as a new storage volume for another mysql database. This operation
creates a new FlexClone volume in FSx for ONTAP.  Note that initially a FlexClone volume
take up almost no additional space; only a pointer table is created to point to the
shared data blocks of the volume it is being cloned from.

The first step is to create a Persistent Volume Claim from the snapshot by executing:
```bash
kubectl create -f manifests/pvc-from-nas-snapshot.yaml
```
To check that it worked, run:
```bash
kubectl get pvc
```
The output should look similar to this:
```bash
$ kubectl get pvc
NAME                     STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS    VOLUMEATTRIBUTESCLASS   AGE
mysql-volume-nas         Bound    pvc-1aae479e-4b27-4310-8bb2-71255134edf0   50Gi       RWO            fsx-basic-nas   <unset>                 125m
mysql-volume-nas-clone   Bound    pvc-ceb1b2c2-de35-4011-8d6e-682b6844bf02   50Gi       RWO            fsx-basic-nas   <unset>                 2m22s
```
To see more details on how the PVC was defined, look at the `manifests/pvc-from-nas-snapshot.yaml` file.

To check it on the FSxN side, you can run:
```bash
FsxId0887a493c777c5122::> volume clone show
                      Parent  Parent        Parent
Vserver FlexClone     Vserver Volume        Snapshot             State     Type
------- ------------- ------- ------------- -------------------- --------- ----
ekssvm  trident_pvc_ceb1b2c2_de35_4011_8d6e_682b6844bf02
                      ekssvm  trident_pvc_1aae479e_4b27_4310_8bb2_71255134edf0
                                            snapshot-bdce9310-9698-4b37-9f9b-d1d802e44f17
                                                                 online    RW
```
### Create a new MySQL database using the cloned volume
Now that you have a new storage volume, you can create a new MySQL database that uses it by executing:
```bash
kubectl create -f manifests/mysql-nas-clone.yaml
```
To check that it is up run:
```bash
kubectl get pods
```
The output should look similar to this:
```bash
NAME                                  READY   STATUS    RESTARTS       AGE
csi-snapshotter-0                     3/3     Running   0              22h
mysql-fsx-nas-695b497757-8n6bb        1/1     Running   0              21h
mysql-fsx-nas-clone-d66d9d4bf-2r9fw   1/1     Running   0              14s
```
### Confirm that the new database is up and running
To confirm that the new database is up and running log into it by running this command:
```bash
kubectl exec -it $(kubectl get pod -l "app=mysql-fsx-nas-clone" --namespace=default -o jsonpath='{.items[0].metadata.name}') -- mysql -u root -p
```
After you have logged in, check that the same data is in the new database:
```
mysql> use fsxdatabase;
mysql> select * from fsx;
+------------+----------+-----------+
| filesystem | capacity | region    |
+------------+----------+-----------+
| netapp01   | 1024GB   | us-east-1 |
| netapp02   | 10240GB  | us-east-2 |
| eks001     | 2048GB   | us-west-1 |
| eks002     | 1024GB   | us-west-2 |
| netapp03   | 1024GB   | us-east-1 |
| netapp04   | 1024GB   | us-west-1 |
+------------+----------+-----------+
6 rows in set (0.00 sec)
```

## Final steps

At this point you don't need the jump server used to configure the EKS environment for
the FSxN File System, so feel free to `terminate` it (i.e. destroy it).

Other than that, you are welcome to deploy other applications that need persistent storage.

## Author Information

This repository is maintained by the contributors listed on [GitHub](https://github.com/NetApp/FSx-ONTAP-samples-scripts/graphs/contributors).

## License

Licensed under the Apache License, Version 2.0 (the "License").

You may obtain a copy of the License at [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an _"AS IS"_ basis, without WARRANTIES or conditions of any kind, either express or implied.

See the License for the specific language governing permissions and limitations under the License.

© 2024 NetApp, Inc. All Rights Reserved.
