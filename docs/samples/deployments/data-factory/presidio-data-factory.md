# Anonymize PII entities in an Azure Data Factory ETL Pipeline

The following samples showcase two scenarios which use Azure Data Factory (ADF) to move a set of JSON objects from an online location to an Azure Storage while anonymizing their content.
The first sample leverages the code for using [Presidio on Azure App Service](../app-service/index.md) to call Presidio as an HTTP REST endpoint in the ADF pipeline while parsing and storing each file as an Azure Blob Storage.
The second sample leverage the code for using [Presidio on spark](../spark/index.md) to run over a set of files on an Azure Blob Storage to anonymize their content, in the case of having a large data set that requires the scale of databricks.

The samples deploy and use the following Azure Services:

* Azure Data Factory - Host and orchestrate the transformation pipeline.
* Azure KeyVault - Holds the access keys for Azure Storage to avoid having keys and secrets in the code.
* Azure Storage - Persistence layer of this sample.
* Azure Databricks/ Azure App Service - Host presidio to anonymize the data.

The input file used by the samples is hosted on [presidio-research](https://github.com/data-privacy-stack/presidio-research/) repository. It is setup as a variable on the provided ARM template and used by Azure Data Factory as the input source.

## Option 1: Presidio as an HTTP REST endpoint

By using Presidio as an HTTP endpoint, the user can select which infrastructure best suits their requirements. in this sample, Presidio is deployed to an Azure App Service, but other deployment targets can be used, such as [kubernetes](../k8s/index.md).

![ADF-App-Service](images/adf-app-service-screenshot.png)

### Deploy the ARM template

Create the Azure App Service and the ADF pipeline by clicking the Deploy-to-Azure button, or by running the following script to provision the [provided ARM template](./arm-templates/azure-deploy-adf-app-service.json).

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fdata-privacy-stack%2Fpresidio%2Fmain%2Fdocs%2Fsamples%2Fdeployments%2Fdata-factory%2Farm-templates%2Fazure-deploy-adf-app-service.json)

```bash
RESOURCE_GROUP=[Name of resource group]
LOCATION=[location of resources]

az group create --name $RESOURCE_GROUP --location $LOCATION
az deployment group create -g $RESOURCE_GROUP --template-file ./arm-templates/azure-deploy-adf-app-service.json
```

Note that:

* A SAS token keys is created and read from Azure Storage and then imported to Azure Key Vault. Using ARM template built in [functions](https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/template-functions): [listAccountSas](https://docs.microsoft.com/en-us/rest/api/storagerp/storageaccounts/listaccountsas).
* An access policy grants the Azure Data Factory managed identity access to the Azure Key Vault by using ARM template [reference](https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/template-functions-resource?tabs=json#reference) function to the Data Factory object and acquire its identity.principalId property. This is enabled by setting the data factory ARM resource's identity attribute to managed identity (SystemAssigned).

### About this Solution Template

This template gets a collection of JSON documents from a file on GitHub. It then extracts one of the text fields of the document, anonymizes the content and uploads it as a text file to the destination store.

The template contains seven activities:

* **GetDataSet**- Copy the dataset from GitHub to the first folder on the Azure Storage blob container (/dataset).
* **LoadSet**- Loads the dataset into the Azure Data Factory memory for processing in a for-each loop.
* **GetSASToken** - Get the SAS token from Azure Key Vault. This will be used later for writing to the blob container.
* **SaveBlobs** - Is a For-Each loop activity. It includes a clause which is executed for each document in the array.
* **PresidioAnalyze** - Sends the text to presidio analyzer endpoint.
* **PresidioAnonymize** - Sends the response from presidio analyzer to presidio anonymizer endpoint.
* **UploadBlob** - Saves the anonymized response from presidio to a randomly named text file on the target Azure Blob Storage.

## Option 2: Presidio on Azure Databricks

By using Presidio as a Notebook step in ADF, we allow Databricks to scale presidio according to the cluster capabilities and the input dataset. Using presidio as a native python package in pyspark can unlock more analysis and de-identification scenarios.

![ADF-Databricks](images/adf-databricks-screenshot.png)

### Pre-requisite - Deploy Azure Databricks

Provision and setup the databricks cluster by following the steps in [presidio-spark sample](../spark/index.md#Deploy-Infrastructure).
Note the output key and export it as DATABRICKS_TOKEN environment variable.

### Deploy the ARM template

Create the rest of the services by running the following script which uses the [provided ARM template](./arm-templates/azure-deploy-adf-databricks.json).

```bash
RESOURCE_GROUP=[Name of resource group]
LOCATION=[location of resources]
DATABRICKS_HOST=https://$DATABRICKS_WORKSPACE_URL
DATABRICKS_CLUSTER_ID=$(databricks clusters get --cluster-name presidio_cluster | jq -r .cluster_id)
DATABRICKS_NOTEBOOK_LOCATION="/notebooks/01_transform_presidio"

az deployment group create -g $RESOURCE_GROUP --template-file ./arm-templates/azure-deploy-adf-databricks.json --parameters Databricks_accessToken=$DATABRICKS_TOKEN Databricks_clusterId=$DATABRICKS_CLUSTER_ID Databricks_notebookLocation=$DATABRICKS_NOTEBOOK_LOCATION Databricks_workSpaceUrl=$DATABRICKS_HOST AzureBlobStorage_accountName=$STORAGE_ACCOUNT_NAME AzureBlobStorage_cotainerName=$STORAGE_CONTAINER_NAME
```

Note that:
Two keys are read from Azure Storage and imported to Azure Key Vault, the account Access Token and a SAS token, using ARM template built in [functions](https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/template-functions): [listAccountSas](https://docs.microsoft.com/en-us/rest/api/storagerp/storageaccounts/listaccountsas) and [listKeys](https://docs.microsoft.com/en-us/rest/api/storagerp/storageaccounts/listkeys).

### About this Solution Template

This template gets a collection of JSON documents from a file on GitHub. It then extracts one of the text fields of the document and saves it to a text file on a temporary folder in the storage account (un-anonymized content). It then runs a spark notebook job that anonymizes the content of the files in that folder and saves the result as csv files on the destination store.

The template contains seven activities:

* **GetDataSet** - Copy the dataset from GitHub to the first folder on the Azure Storage blob container (/dataset).
* **GetSASToken** - Get the SAS token from Azure Key Vault. This will be used later for writing to the blob container.
* **LoadSet** -  Loads the dataset into the Azure Data Factory memory for processing in a for-each loop.
* **SaveBlobs** - Is a For-Each loop activity. It includes a clause which is executed for each document in the array.
* **UploadBlob** - Saves the text file on a temporary container on the target Azure Blob Storage
* **GetSecret** - Get the storage account secret from Azure Key Vault. This will be used later for accessing the blob container from databricks
* **Presidio-Anonymize** - Is a databricks spark job which runs presidio on the temporary storage container. the result of this job is a new container (/output) with csv files that contain the anonymized text.
