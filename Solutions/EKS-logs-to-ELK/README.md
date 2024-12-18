
# Multi log solution using FSxN and Trident on EKS

A multi log solution using NetApp FSxN and Trident for collecting non-stdout logs from applications.

## The problem
* Lets say you have your default application stream but you also want to maintain an access log and an audit log, each log has its own format, its own write frequency and even different permissions.
* There is a need to save each type in a different file but the same goal of collecting these logs and pushing them to log aggregation engines/storage.
* The challenge is that these file are located on the disposable Pod storage and cannot be accessed or streamed same as std out/std error logs.
* A more advance but still common scenario is when a container has more than one log stream / file.

## Collecting logs using FSxN Trident persistent storage

With FSxN and Trident, you can create a shared namespace persistent storage platform and collect non-stdout logs into one location (ElasticSearch, Loki, S3, etc..), overcoming the common obstacles faced when implementing multi log solutions.

## Getting Started

The following section provide quick start instructions for multiple logs shippers. All of these assume that you have cloned this repository locally and you are using a CLI with its current directory set to the root of the code repository.

### Prerequisites

* `helm` - For resource installation. Documenation [here](https://helm.sh/docs/).
* `kubectl` – For interacting with the EKS cluster. Documentation [here](https://kubernetes.io/docs/reference/kubectl/).
* An AWS EKS cluster.
* NetApp FSxN running on the same EKS VPC.
* TCP NFS ports should be open between the EKS nodes and the FSxN: 
    `111`,
    `2049`,
    `635`,
    `4045`,
    `4046`,
    `4049` - [Check NetAppKB instructions](https://kb.netapp.com/onprem/ontap/da/NAS/Which_Network_File_System_NFS_TCP_and_NFS_UDP_ports_are_used_on_the_storage_system)
* Kubernetes Snapshot Custom Resources (CRD) and Snapshot Controller installed on EKS cluster:
  Learn more about the snapshot requirements for your cluster in the ["How to Deploy Volume Snapshots”](https://kubernetes.io/blog/2020/12/10/kubernetes-1.20-volume-snapshot-moves-to-ga/#how-to-deploy-volume-snapshots) Kubernetes blog.
* NetApp Trident operator CSI should be installed on EKS. [Check Trident installation guide using Helm](https://docs.netapp.com/us-en/trident/trident-use/trident-fsx-install-trident.html)

### Installation

* Configure Trident CSI backend to connect to the FSxN file system. First step is to configure a secret for Trident to use to communciate with the FSxN file system.
```
kubectl create secret generic fsx-secret --from-literal=username=fsxadmin --from-literal=password=<your FSxN password> -n trident
```
Next, create a backend configuration for Trident to use to connect to the FSxN file system by running the included helm chart.
* The custom Helm chart includes:
   - `backend-tbc-ontap-nas.yaml` - backend configuration for using NFS on EKS
   - `backend-fsx-ontap-san.yaml` - backend configuration for using ISCSI on EKS (Optional)
   - `storageclass-fsx-nfs.yaml` - Kubernetes storage class for using NFS 
   - `storageclass-fsx-san.yaml` - Kubernetes storage class for using ISCSI (Optional) 
   - `primary-pvc-fsx.yaml` - primary PVC that will be shared cross-namespaces. **NOTE:** The PVC will be created in the `vector` namespace, so if this namespace does not exist, it should be created before running the helm command below. [Check Trident TridentVolumeReference](https://docs.netapp.com/us-en/trident/trident-use/volume-share.html).

The following variables should be filled on the `trident-resources/values.yaml`, or set via the `--set` Helm command line option.

* `namespace` - namespace of the Trident operator. Typically 'trident'.
* `fsx.managment_lif` - FSxN management ip address
* `fsx.svm_name` - FSxN SVM name
* `fsx.data_lif` - FSxN SVM data ip address
* `configuration.storageclass_nas` - NAS storage class name. If you change this, you will need to update the sample application as well.
* `configuration.storageclass_san` - SAN (ISCSI) storage class name

Then use helm to deploy the package:
```
helm install trident-resources ./trident-resources -n trident
```
:bulb: **NOTE:** If this command fails (e.g. because you hadn't created the `vector` namespace first), it still creates a secret under the 'trident' namespace that must deleted before re-running the command. You might see an "cannot re-use a name that is still in use" error when trying to re-run it. Use `kubectl get secrets -n trident` to get the name of the secret, it will look something like `sh.helm.release.v1.trident-resources.v1` and delete it using `kubectl delete secret <secret-name> -n trident`.

Verify that FSxN has been successfully connected to the backend:
```
kubectl get TridentBackendConfig -n trident
```
The output should look similar to this:
```
$ kubectl get tbc -n trident
NAME                    BACKEND NAME            BACKEND UUID                           PHASE   STATUS
backend-fsx-ontap-nas   backend-fsx-ontap-nas   a0195e9b-5e12-456d-a4b8-bd8d41ea4597   Bound   Success
backend-fsx-ontap-san   backend-fsx-ontap-san   bf8f86b4-ff86-4f31-931d-4b5e619a55b1   Bound   Success
```
If the status is not `Success`, then use the following command to get more information:
```
kubectl describe tbc backend-fsx-ontap-nas -n trident
```

### Implementing a sample application for collecting logs

Here is an example of an application that mounts Trident PVC at /log and uses it for cross-namespace PVC.
The yaml files mentioned below are located in the `examples/example-app/templates` directory.

##### **shared-pvc.yaml**:
```
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  annotations:
      trident.netapp.io/shareFromPVC: vector/shared-pv
  name: rpc-app-pvc
  namespace: rpc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: trident-csi
```
Where:
* `trident.netapp.io/shareFromPVC:` The primary PersistentVolumeClaim you have created previously.
* `storage` - volume size
* `storageClassName` - storage class name you set in the `trident-resources/values.yaml` file.

##### **volume-reference-fsx.yaml**:
```
apiVersion: trident.netapp.io/v1
kind: TridentVolumeReference
metadata:
  name: rpc-app-pvc
  namespace: rpc
spec:
  pvcName: shared-pv
  pvcNamespace: vector
```
##### **key parts of the eks-sample-linux-deployment.yaml file**:
```
      volumes:
        - name: task-pv-storage
          persistentVolumeClaim:
            claimName: rpc-app-pvc
```
```
        env:
          - name: POD_NAME
            valueFrom:
              fieldRef:
                apiVersion: v1
                fieldPath: metadata.name
          - name: NODE_NAME
            valueFrom:
              fieldRef:
                apiVersion: v1
                fieldPath: spec.nodeName
```
```
        volumeMounts:
          - mountPath: "/log"
            subPathExpr: $(NODE_NAME)/$(POD_NAME)
            name: task-pv-storage
```
* This mounts FSxN Trident volume to the sample application.
* Adding `POD_NAME`, `NODE_NAME` as environment variables for using `Kubernetes subPathExpr`. In this example, a Pod uses subPathExpr to create a directory `/<current-running-node-name>/<pod-name>` within the mountPath volume `/log`. The mountPath volume takes the Pod name and the Node name from the downwardAPI. The mount directory `/log/<node>/<pod>` is mounted at `/log` in the container and the container writes logs directly to `/log/<node>/<pod>` path. See [Kubernetes subPathExpr example](https://kubernetes.io/docs/concepts/storage/volumes/).

Install the example application by running:
```
helm upgrade --install example-app ./examples/example-app -n rpc --create-namespace
```
To check that it was successfully deployed run:
```
kubectl get pods -n rpc
```
The output should look similar to this:
```
$ kubectl get pod -n rpc
NAME                                          READY   STATUS    RESTARTS   AGE
eks-sample-linux-deployment-858b788c8-f5dw2   1/1     Running   0          39s
eks-sample-linux-deployment-858b788c8-w7zgm   1/1     Running   0          39s
```

When the application is deployed, you should be able to see the PVC as a mount at /log.

### Collecting application logs with a logs collector

There are examples of setting up three different types of log collectors to collect logs from the PVC and stream them to the console. You can read more about each of the log collectors in the following sections.

#### **vector.dev** 
A lightweight, ultra-fast tool for building observability pipelines. Check [vector.dev documentation](https://vector.dev/)

Install Vector.dev agent as DaemonSet from [Helm chart](https://vector.dev/docs/setup/installation/package-managers/helm/) and configure :
1. Clone vector GitHub repository:
``` 
git clone https://github.com/vectordotdev/helm-charts.git
cd helm-charts/charts/vector
```

2. Create a file (**vector-override-values.yaml**) to override the default values:
```
role: "Agent"

image:
  repository: timberio/vector
  tag: "0.35.0-alpine"

existingConfigMaps:
  - "vector-logs-cm"

dataDir: "/vector-data-dir"

service:
  ports:
    - name: prom-exporter
      protocol: TCP
      port: 9090
      targetPort: 9090

extraVolumeMounts:
  - name: shared-logs
    mountPath: /logs
    readOnly: false
    subPathExpr: $(VECTOR_SELF_NODE_NAME)

extraVolumes:
  - name: shared-logs
    persistentVolumeClaim:
      claimName: shared-pv
``` 
* `role: "Agent"` - Deploy vector as DaemonSet.
* `existingConfigMaps` - Adding cutom ConfigMap shown below.
* `extraVolumeMounts` - Mount primary PVC as `/logs/<currnet-node>`, a DaemonSet can only see pods logs on the same host.

3. Create a ConfigMap file (**vector-logs-cm.yaml**) for the Vector stack. This file needs to be put into the `templates` directory.
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: vector-logs-cm
  namespace: vector

data:
  stdout.toml: |
    data_dir = "/vector-data-dir"
    api.enabled = true
    api.address = "0.0.0.0:8686"

    [sources.access_logs]
      type = "file"
      ignore_older_secs = 600
      include = [ "/logs/*/*.log" ]
      read_from = "beginning"

    #Send structured data to console
    [sinks.sink_console]
      type = "console"
      inputs = ["access_logs"]
      target = "stdout"
      encoding.codec = "text"
```

In the example above, collecting logs from [source file](https://vector.dev/docs/reference/configuration/sources/file/) as /logs mount and stream it into the console.
[See more vector Sink configuration](https://vector.dev/docs/reference/configuration/sinks/)

4. Install Vector using override values by running:
```
helm install vector ./  -n vector -f vector-override-values.yaml
```

#### **Filebeat** 
Lightweight shipper for logs. Check [Filebeat documentation](https://github.com/elastic/helm-charts/tree/main/filebeat)

Install Filebeat as DaemonSet from Helm chart and configure:
1. Clone Filebeat GitHub repository:
```
git clone https://github.com/elastic/helm-charts.git
cd helm-charts/filebeat
```
2. Create a file (**filebeat-overide-values.yaml**) to override the default values:
```
daemonset:
  enabled: true
  extraVolumeMounts:
    - name: shared-logs
      mountPath: /logs
      readOnly: false
      subPathExpr: $(NODE_NAME)

  extraVolumes:
    - name: shared-logs
      persistentVolumeClaim:
        claimName: shared-pv
```
3. Create a ConfigMap file (**filebeat-logs-config.yaml**) and place in the templates directory:
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: logs-config
  labels:
    app: '{{ template "filebeat.fullname" . }}-logs-config'
    chart: "{{ .Chart.Name }}-{{ .Chart.Version }}"
    heritage: {{ .Release.Service | quote }}
    release: {{ .Release.Name | quote }}
data:
  filebeat.yml: |
    filebeat.inputs:
      - type: log
        paths:
          - /logs/*/*.log
    output.console:
      pretty: true
```
In the example above, collecting logs from [input Log](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-log.html) as `/logs` mount and stream it into the console.
[See more filebeat output configuration](https://www.elastic.co/guide/en/beats/filebeat/current/configuring-output.html)

4. Adding config map reference to Filebeat DaemonSet:
**daemonset.yaml:**
```
    - name: filebeat-config
    configMap:
        defaultMode: 0600
        name: logs-config
```

5. Install Filebeat using override values:
```
helm install filebeat ./ -n vector -f filebeat-overide-values.yaml
```

#### **Fluent-bit** 
Fluent Bit is an open-source telemetry agent specifically designed to efficiently handle the challenges of collecting and processing telemetry data across a wide range of environments. [Check Fluent-bit documentation](https://docs.fluentbit.io/manual/)

Install fluent-operator from [Helm chart](https://github.com/fluent/helm-charts/tree/main/charts/fluent-operator) and configure:

1. Create an file (**fluentbit-override-values.yaml**) override values:
```
fluentbit:
  enable: true
  input:
    tail:
      enable: true
      path: "/logs/*/*.log"
  output:
    stdout:
      enable: true

  additionalVolumes: 
    - name: shared-logs
      persistentVolumeClaim:
        claimName: shared-pv
  # Pod volumes to mount into the container's filesystem.
  additionalVolumesMounts: 
    - name: shared-logs
      mountPath: /logs
      readOnly: false
      subPathExpr: $(NODE_NAME)
```
2. Install fluent-operator using override values:
```
helm repo add fluent https://fluent.github.io/helm-charts
helm upgrade --install fluent-operator fluent/fluent-operator -n vector --set containerRuntime=containerd -f fluentbit-override-values.yaml
```
## Running Tests

To run tests, connect to the sample application and create a log file under /log:

```bash
# Get the pod names.
kubectl get pods -n rpc
# Connect to the pod replacing POD_NAME with one of the pods from the output above.
kubectl exec -it -n rpc POD_NAME -- /bin/bash
# Run this inside the container:
echo "this is my first log" >> /log/access.log
```
For **vector.dev** you should see:
```
$ kubectl logs -n vector daemonset/vector | grep "this is"
2024-01-21T11:45:31.903153Z  INFO source{component_kind="source" component_id=access_logs component_type=file}:file_server: vector::internal_events::file::source: Found new file to watch. file=/logs/eks-sample-linux-deployment-858b788c8-57gsz/access.log
this is my first log
```
For **filebeat** you should see:
```
"log": {
    "offset": 0,
    "file": {
    "path": "/logs/eks-sample-linux-deployment-858b788c8-57gsz/access.log"
    }
},
"message": "this is my first log",
"input": {
    "type": "log"
}
```
for **Fluent-bit** you should see:
```
$ kubectl logs daemonset/fluent-bit -n vector | grep "this is"
kube.logs.eks-sample-linux-deployment-858b788c8-mrl6l.access.log: [[1705914980.701605366, {}], {"log"=>"this is my first log"}]
```
## Author Information

This repository is maintained by the contributors listed on [GitHub](https://github.com/NetApp/FSx-ONTAP-samples-scripts/graphs/contributors).

## License

Licensed under the Apache License, Version 2.0 (the "License").

You may obtain a copy of the License at [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an _"AS IS"_ basis, without WARRANTIES or conditions of any kind, either express or implied.

See the License for the specific language governing permissions and limitations under the License.

© 2024 NetApp, Inc. All Rights Reserved.
