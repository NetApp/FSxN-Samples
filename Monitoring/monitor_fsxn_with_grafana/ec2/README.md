# Deploy NetApp Harvest on EC2

Harvest installation for monitoring Amazon FSxN using Promethues and Grafana stack, integrating AWS Secret Manager for FSxN credentials.

## Introduction

### What to Expect

Harvest installation will result in the following:
* Install NetApp Harvest with the latest version on your EC2 instance.
* Collecting metrics about your FSxNs and adding existing Grafana dashboards for better visualization.

### Prerequisites
* `EC2` instance – we recommend a `t2.xlarge` instance type with 20GB disk.
* NetApp FSxN running in the same VPC.



#### 1. Create AWS Secret Manager with Username and Password for each FSxN

```sh
aws secretsmanager create-secret --name <YOUR-SECRET-NAME> --secret-string '{"username":"fsxadmin","password":"<YOUR-PASSWORD>"}'
```

#### 2. Create Instance Profile with Permission to AWS Secret Manager and cloudwatch metrics

#### 2.1. Create Policy with Permissions to AWS Secret Manager

```sh
POLICY_ARN=$(aws iam create-policy --policy-name harvest-policy --policy-document file://harvest-Policy.json --query Policy.Arn --output text)
```

#### 2.2. Create Instance Profile Role

```sh
aws iam create-role --role-name HarvestRole --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name HarvestRole --policy-arn $POLICY_ARN
aws iam create-instance-profile --instance-profile-name HarvestProfile
aws iam add-role-to-instance-profile --instance-profile-name HarvestProfile --role-name HarvestRole
```

#### 3. Create EC2 Instance

We recommend using a `t2.xlarge` instance type with 20GB disk and attaching the instance profile.

#### 4. Install Docker and Docker Compose

```sh
yum install docker
sudo curl -L https://download.docker.com/linux/centos/7/x86_64/stable/Packages/docker-compose-plugin-2.6.0-3.el7.x86_64.rpm -o ./compose-plugin.rpm
sudo yum install ./compose-plugin.rpm -y
systemctl start docker
```

#### 5. Install Harvest on EC2

See Harvest official documentation.

##### 5.1. Generate Harvest Configuration File

Create `harvest.yml` file with your cluster details, below is an example with annotated comments. Modify as needed for your scenario.:

```yaml
Exporters:
    prometheus1:
        exporter: Prometheus
        port_range: 12990-14000
        add_meta_tags: false
Defaults:
    use_insecure_tls: true
Pollers:
  fsx01:
        datacenter: fsx
        addr: <FSxN_ip_1>
        collectors:
            - Rest
            - RestPerf
            - Ems
        exporters:
            - prometheus1
        credentials_script:
          path: /opt/fetch-credentails
          schedule: 3h
          timeout: 10s
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
          path: /opt/fetch-credentails
          schedule: 3h
          timeout: 10s
```

In your configuration, add the credentials script section for supporting AWS Secret Manager.

##### 5.2. Generate a Docker Compose from Harvest Configuration

```sh
docker run --rm \
  --env UID=$(id -u) --env GID=$(id -g) \
  --entrypoint "bin/harvest" \
  --volume "$(pwd):/opt/temp" \
  --volume "$(pwd)/harvest.yml:/opt/harvest/harvest.yml" \
  ghcr.io/netapp/harvest \
  generate docker full \
  --output harvest-compose.yml
```

##### 5.3. Replace Harvest images in the harvest-compose.yml:

```yaml
sed -i 's|ghcr.io/netapp/harvest:latest|ghcr.io/tlvdevops/harvest-fsx:latest|g' harvest-compose.yml
```

##### 5.4. Add AWS Secret Manager Names to Docker Compose Environment Variables

`SECRET_NAME` and `AWS_REGION` are required for the credentials script.

```yaml
services:
  fsx01:
    image: ghcr.io/tlvdevops/harvest-fsx:latest
    container_name: poller-fsx01
    restart: unless-stopped
    ports:
      - "12990:12990"
    command: '--poller fsx01 --promPort 12990 --config /opt/harvest.yml'
    volumes:
      - ./cert:/opt/harvest/cert
      - ./harvest.yml:/opt/harvest.yml
      - ./conf:/opt/harvest/conf
    environment:
      - SECRET_NAME=<your_secret_1>
      - AWS_REGION=<your_region>
    networks:
      - backend
```
##### 5.5. Download FSxN dashboards and import into Grafana container:
```yaml
wget https://raw.githubusercontent.com/NetApp/FSx-ONTAP-samples-scripts/main/Monitoring/monitor_fsxn_with_grafana/fsx_dashboards.zip
```
```
unzip fsx_dashboards.zip
```
```
rm -rf grafana/dashboards && mv fsx_dashboards grafana/dashboards
```

##### 5.6. Generate yet-another-exporter configuration:
```yace-config.yaml:``` 
replace the region with your FSxN regoin.
```yaml
apiVersion: v1alpha1
sts-region: <your_region>
discovery:
  jobs:
    - type: AWS/FSx
      regions: [<your_region>]
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

##### 5.7. Add Yet-Another-Exporter to harvest-compose.yaml

```yaml
  yace:
    image: quay.io/prometheuscommunity/yet-another-cloudwatch-exporter:latest
    container_name: yace
    restart: always
    expose:
      - 8080
    volumes:
      - ./yace-config.yaml:/tmp/config.yml
      - $HOME/.aws:/exporter/.aws:ro
    command:
      - -listen-address=:8080
      - -config.file=/tmp/config.yml
    networks:
      - backend
```

##### 5.7. Add Yet-Another-Exporter target to prometheus.yml:
```yaml
cat <<EOF >> container/prometheus/prometheus.yml
- job_name: 'yace'
  static_configs:
    - targets: ['yace:8080']
EOF
```

##### 6. Bring Everything Up

```sh
docker compose -f prom-stack.yml -f harvest-compose.yml up -d --remove-orphans
```

After bringing up the prom-stack.yml compose file, you can access Grafana at 
http://IP_OF_GRAFANA:3000.

You will be prompted to create a new password the first time you log in. Grafana's default credentials are:
```
username: admin
password: admin
```