# NetApp Harvest Deployment Guide

This repository provides instructions on how to deploy NetApp Harvest on Amazon EC2 and Amazon EKS. NetApp Harvest is a data collection tool designed to gather operational metrics from ONTAP systems. These metrics can then be used for monitoring, troubleshooting, and optimizing resources.

## Solutions

- **EC2 Deployment:** This solution involves setting up NetApp Harvest on an Amazon EC2 instance. It includes the installation of Docker and Docker Compose, the creation of AWS Secret Manager secrets, and the configuration of IAM roles and policies. [Read More](./ec2/README.md)

- **EKS Deployment:** This solution involves deploying NetApp Harvest on an Amazon EKS cluster using Helm. It also includes the setup of AWS Secret Manager secrets, the configuration of IAM roles and policies, and the integration with Prometheus and Grafana for metrics visualization. [Read More](./eks/README.md)

Each solution has its own set of prerequisites and detailed installation steps. Please refer to the respective README files for detailed instructions.
