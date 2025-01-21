# helm-oci-autonomous-db


[![License: UPL](https://img.shields.io/badge/license-UPL-green)](https://img.shields.io/badge/license-UPL-green) [![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=oracle-devrel_terraform-oci-arch-ci-cd)](https://sonarcloud.io/dashboard?id=oracle-devrel_terraform-oci-arch-ci-cd)


## Introduction

This Helm Chart makes it easy to create and manage an Autonomous Database (ATP) from a Kubernetes cluster deployed within Oracle Cloud Infrastructure (OCI). The Kubernetes cluster can be deployed using Oracle Container Engine for Kubernetes (OKE) or a customer-managed cluster deployed on virtual machine instances.


This Helm chart relies on the OCI Service Operator for Kubernetes (OSOK), and it is a pre-requisite to have OSOK deployed within the cluster to use this Helm chart.


## Pre-requisites

- A Kuberntes cluster deployed in OCI 
- [OCI Service Operator for Kuberntes (OSOK) deployed in the cluster](https://github.com/oracle/oci-service-operator/blob/main/docs/installation.md)
- [kubectl installed and using the context for the Kubernetes cluster where the ATP resource will be deployed](https://kubernetes.io/docs/tasks/tools/)
- [Helm installed](https://helm.sh/docs/intro/install/)
- [Docker installed](https://docs.docker.com/engine/install/)


##  Getting Started

**1. Clone or download the contents of this repo** 
     
     git clone https://github.com/oracle-devrel/helm-oci-autonomous-db.git

**2. Change to the directory that holds the Helm Chart** 

      cd ./helm-oci-autonomous-db

**3. Populate the values.yaml file with information to deploy the Autonomous Database resource**


**4. Create the namespace where the ATP resource will be deployed**

     kubectl create ns <namespace name>

**5. Install the Helm chart. Best practice is to assign the databse password and wallet password during the installation of the Helm chart instead of adding it to the values.yam file.**

     helm -n <namespace name> install \
     --set dbPassword=<database password> \  
     --set walletPassword=<wallet password> \
       <name for this install> .
  
  ***Example:***
     helm -n autodb  --set dbPassword=Admin!2345  --set walletPassword=Admin!2345 autodb .   
     
The password must be between 8 and 32 characters long, and must contain at least 1 numeric character, 1 lowercase character, 1 uppercase character, and 1        special (nonalphanumeric) character.


**6. List the Helm installation**

     helm  -n <namespace name> ls


**7. To uninstall the Helm chart**

     helm uninstall -n <namespace name> <name of the install> .
     
     
   **Important Note**
 
Uninstalling the helm chart will only remove the ATP resource from the cluster and not OCI. You will need to use the console or the OCI CLI to remove the ATP from OCI. This function is to prevent accidental deletion of the database.

     
  **Notes/Issues:**
 
 Provisioning the Autonomous Database (ATP) can take up to 5 minutes. 
 
 To confirm that the ATP is active, run the following command and check the status of the ATP system.

```sh
$ kubectl -n <name of namespace> get autonomousdatabases -o wide
NAME            DISPLAYNAME     DBWORKLOAD   STATUS   OCID                                                                                            AGE
autodbtest301   autodbtest301   OLTP         Active   ocid1.autonomousdatabase.oc1.iad.anuwcljsnlc5nbyazyyzlqxytdmghb5eyafntqnxq6cupu3zmxf6jihz6vna   28m
```

 ## Accessing the Database

Once the  ATP is ready, a secret with the name defined in values.yaml file under wallet.walletName will be created to expose the wallet files required to connect to the ATP.


| Parameter          | Description                                                              | Type   |
| ------------------ | ------------------------------------------------------------------------ | ------ |
| `ewallet.p12`      | Oracle Wallet.                                                           | string |
| `cwallet.sso`      | Oracle wallet with autologin.                                            | string |
| `tnsnames.ora`     | Configuration file containing service name and other connection details. | string |
| `sqlnet.ora`       |                                                                          | string |
| `ojdbc.properties` |                                                                          | string |
| `keystore.jks`     | Java Keystore.                                                           | string |
| `truststore.jks`   | Java trustore.                                                           | string |
| `user_name`        | Pre-provisioned DB ADMIN Username.                                       | string |



**1. You can extract the wallet files with the check_autodb.py script in the python directory**. 

The script will check for the creation of the secret. It will check every 5 seconds until the secret is created and then write the files to a designated directory. Modify the following variables in the script before running.  

**path to write wallet files**.   
path = (' ')

**namespace where Autonomous Database was deployed**.   
namespace =('')

**secret_name is the name assigned to the secret defined in values.yaml file wallet.walletName**   
secret_name = ('')


```     
   $  cd ./python
   $  python3 check_autodb.py
```

**2. Package the Python script into a container image**. 

You may want to run the Python script inside the Kubernetes cluster and make the wallet files available to your application to access the ATP. The script will need to be packaged into a container image before running in a Kubernetes cluster. Before building the image, you will need to modify the variables to read from environmental variables in the script. The variables can then be passed to the container as env variables when deployed. This is detailked in the comments of the script.



```     
     **Build Image**
     cd ./python
     docker build -t <repository>/<name of image>:<tag> .
     
     example:
     docker build -t docker build -t chiphwang/checkautodb:1.9 .  
     
     **Push Image into Repo**
     docker push docker build -t chiphwang/checkautodb:1.9 
     
```

**3. Deploy the container image into a Kubernetes cluster**. 

One way to use the packaged Python script is to use it in an init-container for the application container in a Kubernetes pod. The init-container will run, and when the ATP is ready, it will write the wallet files to a location that is accessible to the application container.

Since the Kubernetes pod will be contacting the Kubernetes API server to check for the creation of secrets, the appropriate permissions need to the assigned to the pod. In the templates directory, the role.yaml, the role-binding.yaml file sets the permissions to access secrets to the internal-kubectl service account. This service account will need to be assigned to the Kubernetes pod to read secrets from the Kubernetes API server.

In the following example, the pods in the deployment are assigned the service account internal-kubectl, which has permission to contact the Kubernetes API server to read secrets. The init-container and the application container have the wallet volume mounted and is accessible to both. The init-container will run the Python script and write the wallet files to the wallet volume, where the application container can read the files
```

apiVersion: apps/v1 
kind: Deployment
metadata:
  name: wordpress
  labels:
    app: wordpress
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wordpress
      tier: frontend
  strategy:
    type: Recreate    
  template:
    metadata:
      labels:
        app: wordpress
        tier: frontend
    spec:
      serviceAccountName: internal-kubectl # service acccount with permission to read secrets from the cluster
      initContainers:
      - name: db-init
        image: chiphwang/checkautodb:1.9  # image with the packaged python script
        command: [ "sh", "-c", "python check_autodb.py" ] # command to run the python script
        env:
        - name: namespace
          value: {{ .Release.Namespace }}
        - name: path
          value: '/wallet'  # shared mount point accessible by init-container and application container
        - name: secret_name
          value: {{ .Values.walletName }}
        volumeMounts:
        - name: wallet
          mountPath: /wallet
      containers:
      - image: {{ .Values.wordpressImageName}}
        name: wordpress
        command: [ "/bin/bash", "-c", "source /tmp/host/launch.sh && docker-entrypoint.sh apache2-foreground" ]
        env:
        - name: WORDPRESS_DB_PASSWORD
          value: {{ .Values.database.password }} 
        - name: WORDPRESS_DB_NAME
          value: {{ .Values.DBName }} 
        - name: WORDPRESS_DB_USER
          value: {{ .Values.database.username }} 
        ports:
        - containerPort: 80
          name: wordpress
        volumeMounts:
        - name: wallet
          mountPath: /wallet  # shared mount point accessible by init-container and application container
      volumes:
      - name: wallet # shared volume accessible by init-container adn application container
        emptyDir: {}



```

## Autonomous Database Specification Parameters

The Complete Specification of the `AutonomousDatabase` Custom Resource (CR) is as detailed below:

| Parameter                          | Description                                                         | Type   | Mandatory |
| ---------------------------------- | ------------------------------------------------------------------- | ------ | --------- |
| `spec.id` | The Autonomous Database [OCID](https://docs.cloud.oracle.com/Content/General/Concepts/identifiers.htm). | string | no  |
| `spec.displayName` | The user-friendly name for the Autonomous Database. The name does not have to be unique. | string | yes       |
| `spec.dbName` | The database name. The name must begin with an alphabetic character and can contain a maximum of 14 alphanumeric characters. Special characters are not permitted. The database name must be unique in the tenancy. | string | yes       |
| `spec.compartmentId` | The [OCID](https://docs.cloud.oracle.com/Content/General/Concepts/identifiers.htm) of the compartment of the Autonomous Database. | string | yes       |
| `spec.cpuCoreCount` | The number of OCPU cores to be made available to the database. | int    | yes       |
| `spec.dataStorageSizeInTBs`| The size, in terabytes, of the data volume that will be created and attached to the database. This storage can later be scaled up if needed. | int    | yes       |
| `spec.dbVersion` | A valid Oracle Database version for Autonomous Database. | string | no        |
| `spec.isDedicated` | True if the database is on dedicated [Exadata infrastructure](https://docs.cloud.oracle.com/Content/Database/Concepts/adbddoverview.htm).  | boolean | no       |
| `spec.dbWorkload`  | The Autonomous Database workload type. The following values are valid:  <ul><li>**OLTP** - indicates an Autonomous Transaction Processing database</li><li>**DW** - indicates an Autonomous Data Warehouse database</li></ul>  | string | yes       |
| `spec.isAutoScalingEnabled`| Indicates if auto scaling is enabled for the Autonomous Database OCPU core count. The default value is `FALSE`. | boolean| no        |
| `spec.isFreeTier` | Indicates if this is an Always Free resource. The default value is false. Note that Always Free Autonomous Databases have 1 CPU and 20GB of memory. For Always Free databases, memory and CPU cannot be scaled. | boolean | no |
| `spec.licenseModel` | The Oracle license model that applies to the Oracle Autonomous Database. Bring your own license (BYOL) allows you to apply your current on-premises Oracle software licenses to equivalent, highly automated Oracle PaaS and IaaS services in the cloud. License Included allows you to subscribe to new Oracle Database software licenses and the Database service. Note that when provisioning an Autonomous Database on [dedicated Exadata infrastructure](https://docs.oracle.com/iaas/Content/Database/Concepts/adbddoverview.htm), this attribute must be null because the attribute is already set at the Autonomous Exadata Infrastructure level. When using [shared Exadata infrastructure](https://docs.oracle.com/iaas/Content/Database/Concepts/adboverview.htm#AEI), if a value is not specified, the system will supply the value of `BRING_YOUR_OWN_LICENSE`. <br>Allowed values are:<ul><li>LICENSE_INCLUDED</li><li>BRING_YOUR_OWN_LICENSE</li></ul>. | string | no       |
| `spec.freeformTags` | Free-form tags for this resource. Each tag is a simple key-value pair with no predefined name, type, or namespace. For more information, see [Resource Tags](https://docs.oracle.com/iaas/Content/General/Concepts/resourcetags.htm). `Example: {"Department": "Finance"}` | string | no |
| `spec.definedTags` | Defined tags for this resource. Each key is predefined and scoped to a namespace. For more information, see [Resource Tags](https://docs.oracle.com/iaas/Content/General/Concepts/resourcetags.htm). | string | no |
| `spec.adminPassword.secret.secretName` | The Kubernetes Secret Name that contains admin password for Autonomous Database. The password must be between 12 and 30 characters long, and must contain at least 1 uppercase, 1 lowercase, and 1 numeric character. It cannot contain the double quote symbol (") or the username "admin", regardless of casing. | string | yes       |
| `spec.wallet.walletName` | The Kubernetes Secret Name of the wallet which contains the downloaded wallet information. | string | yes       |
| `spec.walletPassword.secret.secretName`| The Kubernetes Secret Name that contains the password to be used for downloading the Wallet. | string |  no  |

## Useful commands 


**1. To check the status of the Autonomous Database System run the following command**
     
     kubectl -n <namespace of autonomousdatabase> get autonomousdatabases -o wide

**2. To describe the  Autonomous Database System  run the following command** 
     
     kubectl -n <namespace of autonomousdatabase> describe autonomousdatabases 

**3. To retreive the OCID of Autonomous Database System run the following command** 

      kubectl -n <namespace of autonomousdatabase> get autonomousdatabase <name of mysqldbsystem> -o jsonpath="{.items[0].status.status.ocid}
      

**4. To retrive the wallet password of the Autonomous Database System run the following command**
     
    kubectl -n   <autonomousdatabase>   get secret <name of wallet secret>  -o  jsonpath="{.data.walletPassword}" | base64 --decode





## Additional Resources

- [OCI Service Operator for Kuberntes (OSOK) deployed in the cluster](https://github.com/oracle/oci-service-operator)
- [OCI Autonomous Database Serice OSOK](https://github.com/oracle/oci-service-operator/blob/main/docs/adb.md)
- [Oracle Autonomous Database](https://www.oracle.com/database/what-is-autonomous-database/)
- [Developing Python Applications for Oracle ATP](https://www.oracle.com/database/technologies/appdev/python/quickstartpython.html)


## License
Copyright (c) 2024 Oracle and/or its affiliates.

Licensed under the Universal Permissive License (UPL), Version 1.0.

See [LICENSE](LICENSE.txt) for more details.
