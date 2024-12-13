# Monitoring Overview
This subfolder contains tools that can help you monitor your FSx ONTAP file system.

| Tool | Description |
| --- | --- |
| [Automatically Add Cloud Watch Alarms](/Monitoring/auto-add-cw-alarms) | This tool will automatically add CloudWatch alarms that will alert you when:<br><ul><li>The utilization of the primary storage of any FSx ONTAP file system gets above a specified threshold.</li><li>The CPU utilization of any file system gets above a specified threshold.</li><li>The utilization of any volume within any file system gets above a specified threshold.</li></ul>|
| [CloudWatch Dashboard for FSx for ONTAP](/Monitoring/CloudWatch-FSx) | This tool creates a CloudWatch dashboard that displays metrics for your FSx for ONTAP file system. |
| [Ingest FSX for ONTAP NAS audit logs into CloudWatch](/Monitoring/ingest_nas_audit_logs_into_cloudwatch) | This tool helps you ingest the FSx for ONTAP NAS audit logs into CloudWatch. |
| [LUN Monitoring](/Monitoring/LUN-monitoring) | This tool exports FSxN LUN metrics to CloudWatch and creates a CloudWatch dashboard to you can monitor your LUNs. |
| [Monitor ONTAP Services](/Monitoring/monitor-ontap-services)| This tool helps you monitor various Data ONTAP services and send SNS alerts if anything of interest is detected. The following services are monitored:<br><ul><li>EMS Messages</li><li>SnapMirror health, including tag time</li><li>Aggregate, volume or Quota utilization based on user provided thresholds</li><li>Overall health of the File System</ul>|
| [Monitor FSxN with Harvest on EKS](/Monitoring/monitor_fsxn_with_harvest_on_eks) | This tool helps you install Harvest, and Prometheus and Grafana if needed, into your EKS cluster so you can use them to monitor an FSx file system. |

## Author Information

This repository is maintained by the contributors listed on [GitHub](https://github.com/NetApp/FSx-ONTAP-samples-scripts/graphs/contributors).

## License

Licensed under the Apache License, Version 2.0 (the "License").

You may obtain a copy of the License at [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an _"AS IS"_ basis, without WARRANTIES or conditions of any kind, either express or implied.

See the License for the specific language governing permissions and limitations under the License.

© 2024 NetApp, Inc. All Rights Reserved.
