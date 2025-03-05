# Deploy NetApp Harvest on EKS 

Harvest helm chart for monitoring Amazon multiple FSxN on existing monitoring stack and integrating AWS Secret Manager for FSxN credentails.



## Introduction

### What to expect

Harvest Helm chart installation will result the following:
* Install NetApp Harvest with latest version on your EKS
* Each FSxN cluster will represent as kubernetes pod on the cluster.
* Collecting metrics about your FSxNs and adding existing Grafana dashboards for better visualizion.

### Prerequisites
* `Helm` - for reources installation
* NetApp FSxN running on the same EKS vpc.
* Existing `Promethues` running on your EKS cluster.
* Existing `Grafana` running on your EKS cluster.
* Existing `Secret Manager` on the same FSxN region.


### Deployment
### User Input

Parameter | Description | 
--- | --- | 
fsxs.clusters.name | FSxN cluster name | 
fsxs.clusters.managment_lif | FSxN for NetApp ONTAP filesystem management IP |
fsxs.clusters.secretName | AWS Secret Manager for FSxN credentials |
fsxs.clusters.region | FSxN and AWS Secret Manager region |
fsxs.clusters.promPort | Which port harvest will be created and exposed to Promethues |
promethues | Existing Promethues name for discovering |

### Integration with AWS Secret Manager

The installation supports integration with AWS Secret Manager. You can store your FSxN credentials by using existing or new AWS Secret Manager. 
Harvest will invoke script specified in the credentials_script path section which already mapped to Harvest container.
Harvest uses ServiceAccount with permissions to fetch the secrets. 
Credentails script expect to fetch `USERNAME`, `PASSWORD` values from Secret Manager.
ServiceAccount should be created during the installation with the sufficient permissions. 


### Monitoring multiples FSxN

The Helm chart supports monitoring multiple FSxNs.
You can add multiples FSxNs by configure it on `values.yaml`:
For example: 
```
fsxs:
  clusters:
  - name: fsx1
    managment_lif: 1.1.1.1
    promPort: 12990
    secretName: secret1
    region: us-east-1
  - name: fsx2
    managment_lif: 1.1.1.1
    promPort: 12990
    secretName: secret2
    region: us-east-1
```

### Installation
Install Harvest helm chart from this GitHub repository. The custom Helm chart includes:
* `deplyment.yaml` - Harvest deployment using Harvest latest version image
* `harvest-config.yaml` - Harvest backend configuration
* `harvest-cm.yaml` -  Environment variables configuration for credentails script.
* `service-monitor.yaml` - Promethues ServiceMonitor for collecting Harvest metrics.

1. **(optional) Create AWS secret manager**
```
aws secretsmanager create-secret \
  --region <REGION> \
  --name <SECRET_NAME> \
  --secret-string '{"USERNAME":"'fsxadmin'", "PASSWORD":"'<YOUR_FSX_PASSWORD'"}
```

2. **Create ServiceAccount with permissions to AWS Secret Manager**

**Create Policy with permissions to AWS secretsmanager:**

The following IAM policy can be used to grant the all permissions required by Harvest to fetch the secrets:

```
{
    "Statement": [
        {
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecrets"
            ],
            "Effect": "Allow",
            "Resource": [
                "<your_secret_manager_arn_1>",
                "<your_secret_manager_arn_2>"
            ]
        }
    ],
    "Version": "2012-10-17"
}

```
* keep the POLICY_ARN for the ServiceAccount creation.


**Create ServiceAccount**:

**note**: namespace should be already exists\
if not exist use the following command: 
```
kubectl create ns <NAMESPACE>
```
```
eksctl create iamserviceaccount --name harvest-sa --region=<REGION> --namespace <NAMESPACE> --role-name harvest-role --cluster <YOUR_CLUSTER_NAME> --attach-policy-arn "<POLICY_ARN>" --approve
```

3. **Install Harvest helm chart**
```text
helm upgrade --install harvest  -f values.yaml ./ --namespace=<NAMESPACE> --set promethues=<your_promethues_release_name>
```

Once the deployment is complete, Harvest should be listed as a target on Promethues.

### Import FSxN CloudWatch metrics into your monitoring stack
AWS provides more metrics which cannot be collected by Harvest.
We recommand to use yet-another-exporter (by Promethues community) for collecting metrics from CloudWatch. see: https://github.com/nerdswords/helm-charts

#### Installation #### 
1. **Create ServiceAccount with permissions to AWS CloudWatch**
The following IAM policy can be used to grant the all permissions required by yet-another-exporter to fetch the CloudWatch metrics:

```
{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "tag:GetResources",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "apigateway:GET",
          "aps:ListWorkspaces",
          "autoscaling:DescribeAutoScalingGroups",
          "dms:DescribeReplicationInstances",
          "dms:DescribeReplicationTasks",
          "ec2:DescribeTransitGatewayAttachments",
          "ec2:DescribeSpotFleetRequests",
          "shield:ListProtections",
          "storagegateway:ListGateways",
          "storagegateway:ListTagsForResource"
        ],
        "Effect": "Allow",
        "Resource": "*"
      }
    ]
  }

```
Run the following command in order to create the policy:

POLICY_ARN=$(aws iam create-policy --policy-name yace-exporter-policy --policy-document file://yace-exporter-policy.json --query Policy.Arn --output text)

2. **Create ServiceAccount**:

**note**: namespace should be already exists\
if not exist use the following command: 
```
kubectl create ns <NAMESPACE>
```
```
eksctl create iamserviceaccount --name yace-exporter-sa --region=<REGION> --namespace <NAMESPACE> --role-name yace-cloudwatch-exporter-role --cluster <YOUR_CLUSTER_NAME> --attach-policy-arn "$POLICY_ARN" --approve
```

3. **Install yace-exporter helm chart**

```text
helm repo add nerdswords https://nerdswords.github.io/helm-charts
```

Change the promethues release name for ServiceMonitor creation on yace-override-values.yaml:
```
serviceMonitor:
  enabled: true
  labels:
    release: <Promethues_Name>
```

Apply the region name to FSxN's region on yace-override-values.yaml:
```
  apiVersion: v1alpha1
  sts-region: <Region_Name>
  discovery:
    jobs:
    - type: AWS/FSx
      regions:
        - <Region_Name>
      period: 300
      length: 300
      metrics:
      - name: DiskReadOperations
        statistics: [Average]
      - name: DiskWriteOperations
        statistics: [Average]
      - name: DiskReadBytes
        statistics: [Average]
      - name: DiskWriteBytes
        statistics: [Average]
      - name: DiskIopsUtilization
        statistics: [Average]
      - name: NetworkThroughputUtilization
        statistics: [Average]
      - name: FileServerDiskThroughputUtilization
        statistics: [Average]
```

```text
helm install nerdswords/yet-another-cloudwatch-exporter -f yace-override-values.yaml
```



### Adding Grafana dashboards and visualize your FSxN metrics on Grafana
Import existing dashboards into your Grafana:
* [How to import Grafana dashboards](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/import-dashboards/)
* Example dashboards for Grafana are located in the dashboards folder
#### Note
 fsxadmin user does not have a full permission to collect all metrics by default.