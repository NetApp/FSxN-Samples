# Harvest and Grafana Deployment using AWS CloudFormation

This guide provides instructions to deploy the Harvest and Grafana environment to monitor your Amazon FSx for NetApp ONTAP resources. The deployment process takes about five minutes.

## Prerequisites

Before you start, ensure you have the following:
- An FSx for ONTAP file system running in an Amazon Virtual Private Cloud (Amazon VPC) in your AWS account.
- The parameter information for the template.

## Yet Another CloudWatch Exporter (YACE)

YACE, or Yet Another CloudWatch Exporter, is a Prometheus exporter for AWS CloudWatch metrics. It is written in Go and uses the official AWS SDK. YACE supports auto-discovery of resources via tags, structured logging, filtering monitored resources via regex, and more[1](https://github.com/prometheus-community/yet-another-cloudwatch-exporter). This deployment includes YACE to enhance monitoring capabilities for your FSx for ONTAP resources.

## Overview

This deployment includes:
- **Yet Another CloudWatch Exporter (YACE)**: Collects FSxN CloudWatch metrics.
- **Harvest**: Collects ONTAP metrics.

## Deployment Steps

1. **Download the Template**
   - Download the `fsx-ontap-harvest-grafana.template` AWS CloudFormation template.

2. **Create the Stack**
   - Open the AWS CloudFormation console.
   - Choose **Create stack** and upload the `fsx-ontap-harvest-grafana.template` file.

3. **Specify Stack Details**
   - **Parameters**: Review and modify the parameters as needed for your file system. The default values are:
     - **InstanceType**: `t3.micro` (Other options: `t3.small`, `t3.medium`, `t3.large`, `t3.xlarge`, `t3.2xlarge`, etc.)
     - **KeyPair**: No default value. Specify the key pair to access the EC2 instance.
     - **SecurityGroup**: No default value. Ensure inbound ports 3000 and 9090 are open.
     - **SubnetType**: No default value. Choose `public` or `private`.
     - **Subnet**: No default value. Specify the same subnet as your FSx for ONTAP file system's preferred subnet.
     - **LatestLinuxAmiId**: `/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2`
     - **FSxEndPoint**: No default value. Specify the management endpoint IP address of your FSx file system.
     - **SecretName**: No default value. Specify the AWS Secrets Manager secret name containing the password for the `fsxadmin` user.

4. **Configure Stack Options**
   - Choose **Next** for stack options.

5. **Review and Create**
   - Review the stack details and confirm the settings.
   - Select the check box to acknowledge that the template creates IAM resources.
   - Choose **Create stack**.

6. **Monitor Stack Creation**
   - Monitor the status of the stack in the AWS CloudFormation console. The status should change to `CREATE_COMPLETE` in about five minutes.

## Accessing Grafana

- After the deployment is complete, log in to the Grafana dashboard using your browser:
  - URL: `http://<EC2_instance_IP>:3000`
  - Default credentials:
    - Username: `admin`
    - Password: `admin`
  - **Note**: Change your password immediately after logging in.

## Supported Harvest Dashboards

Amazon FSx for NetApp ONTAP exposes a different set of metrics than on-premises NetApp ONTAP. Therefore, only the following out-of-the-box Harvest dashboards tagged with `fsx` are currently supported for use with FSx for ONTAP. Some panels in these dashboards may be missing information that is not supported:

- **FSxN_Clusters**
- **FSxN_CW_Utilization**
- **FSxN_Data_protection**
- **FSxN_LUN**
- **FSxN_SVM**
- **FSxN_Volume**

---

## Monitor More FSxN

To monitor additional FSxN resources, follow these steps:

1. **Move to the Harvest Directory**
   - Navigate to the Harvest directory:
     ```bash
     cd /opt/harvest
     ```

2. **Configure Additional FSxN in `harvest.yml`**
   - Edit the `harvest.yml` file to add the new FSxN configuration. For example:
     ```yaml
     fsx02:
       datacenter: fsx
       addr: <FSxN_ip_2>
       collectors:
         - Rest
         - RestPerf
         - Ems
       exporters:
         - prometheus1
       credentials_script:
         path: /opt/fetch-credentials
         schedule: 3h
         timeout: 10s
     ```

3. **Update `harvest-compose` with the Additional FSxN**
   - Edit the `harvest-compose.yml` file to include the new FSxN configuration:
     ```yaml
     fsx02:
       image: ghcr.io/tlvdevops/harvest-fsx:latest
       container_name: poller-fsx02
       restart: unless-stopped
       ports:
         - "12991:12991"
       command: '--poller fsx02 --promPort 12991 --config /opt/harvest.yml'
       volumes:
         - ./cert:/opt/harvest/cert
         - ./harvest.yml:/opt/harvest.yml
         - ./conf:/opt/harvest/conf
       environment:
         - SECRET_NAME=<your_secret_2>
         - AWS_REGION=<your_region>
     ```
   - **Note**: Change the `container_name`, `ports`, `promPort`, and `SECRET_NAME` as needed.

4. **Add FSxN to Prometheus Targets**
   - Edit the `harvest_targets.yml` file to add the new FSxN target:
     ```yaml
     - targets: ['<container_name>:<container-port>']
     ```

5. **Restart Docker Compose**
   - Bring down the Docker Compose stack:
     ```bash
     docker compose -f prom-stack.yml -f harvest-compose.yml down     ```
   - Bring the Docker Compose stack back up:
     ```bash
     docker compose -f prom-stack.yml -f harvest-compose.yml up -d --remove-orphans
     ```

---

Feel free to adjust the placeholders (`<FSxN_ip_2>`, `<your_secret_2>`, `<your_region>`, `<container_name>`, `<container-port>`) with your specific details.
## Additional Information


---

[1](https://github.com/prometheus-community/yet-another-cloudwatch-exporter): [Yet Another CloudWatch Exporter on GitHub](https://github.com/prometheus-community/yet-another-cloudwatch-exporter)