# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC # Setup Notebook for chatbot hackathon
# MAGIC
# MAGIC !Please make sure to execute this notebook with the same runtime and instance type for the participants.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Step1: Install Dependencies
# MAGIC
# MAGIC Because there is no internet connection for participant clusters we need to download and install all the dependencies from local path. 
# MAGIC
# MAGIC If the **dependencies.tar.gz is being used**, **the following steps (until init script) can be ignored**. Check the **dependencies** folder and the import **dependencies notebook** instead. 

# COMMAND ----------

# DBTITLE 1,Create requirements.txt
# MAGIC %sh
# MAGIC #!/bin/bash
# MAGIC
# MAGIC
# MAGIC # Define path for requirements.txt file
# MAGIC echo "Setting up requirements.txt file..."
# MAGIC REQUIREMENTS_FILE_PATH="/databricks/driver/dependencies/requirements.txt"
# MAGIC
# MAGIC # Check if requirements.txt file exists
# MAGIC if [ -e "$REQUIREMENTS_FILE_PATH" ]; then
# MAGIC   echo "requirements.txt already exists at $REQUIREMENTS_FILE_PATH"
# MAGIC   echo "Deleting requirements.txt..."
# MAGIC   rm -f $REQUIREMENTS_FILE_PATH
# MAGIC fi
# MAGIC
# MAGIC mkdir -p "/databricks/driver/dependencies/"
# MAGIC
# MAGIC # Create and open the file in write mode
# MAGIC cat > $REQUIREMENTS_FILE_PATH <<EOF
# MAGIC anyio==3.7.1 
# MAGIC backoff==2.2.1 
# MAGIC chromadb==0.3.22 
# MAGIC clickhouse-connect==0.6.11 
# MAGIC duckdb==0.8.1 
# MAGIC exceptiongroup==1.1.3 
# MAGIC fastapi==0.103.1 
# MAGIC h11==0.14.0 
# MAGIC hnswlib==0.7.0 
# MAGIC httptools==0.6.0 
# MAGIC lz4==4.3.2 
# MAGIC monotonic==1.6 
# MAGIC numpy==1.24.4 
# MAGIC posthog==3.0.2 
# MAGIC python-dotenv==1.0.0 
# MAGIC sniffio==1.3.0 
# MAGIC starlette==0.27.0 
# MAGIC typing-extensions==4.7.1 
# MAGIC uvicorn==0.23.2 
# MAGIC uvloop==0.17.0 
# MAGIC watchfiles==0.20.0 
# MAGIC websockets==11.0.3 
# MAGIC zstandard==0.21.0
# MAGIC numba==0.57.1
# MAGIC llvmlite==0.40.1
# MAGIC mleap==0.23.0 
# MAGIC scikit-learn==1.0.2
# MAGIC EOF

# COMMAND ----------

# DBTITLE 1,Download missing dependencies
# MAGIC %sh
# MAGIC #!/bin/bash
# MAGIC
# MAGIC # Define path for requirements.txt file
# MAGIC echo "Using requirements.txt file..."
# MAGIC REQUIREMENTS_FILE_PATH="/databricks/driver/dependencies/requirements.txt"
# MAGIC
# MAGIC # Check if the directory exists
# MAGIC if [ -d "/databricks/driver/dependencies/packages" ]; then
# MAGIC     # Check if the directory is empty
# MAGIC     if [ ! "$(ls -A /databricks/driver/dependencies/packages)" ]; then
# MAGIC         echo "The directory /databricks/driver/dependencies/packages is empty."
# MAGIC     else
# MAGIC         # Remove all files from the directory
# MAGIC         rm -rf /databricks/driver/dependencies/packages/*
# MAGIC         echo "Removed all files from /databricks/driver/dependencies/packages."
# MAGIC     fi
# MAGIC else
# MAGIC     # Create the directory if it doesn't exist
# MAGIC     mkdir -p /databricks/driver/dependencies/packages
# MAGIC     echo "Created the directory /databricks/driver/dependencies/packages."
# MAGIC fi
# MAGIC
# MAGIC # Download packages to 'packages' directory inside 'dependencies' directory
# MAGIC echo "Downloading packages..."
# MAGIC pip download -r $REQUIREMENTS_FILE_PATH --no-deps -d /databricks/driver/dependencies/packages/
# MAGIC echo "Packages downloaded to /databricks/driver/dependencies/packages/"
# MAGIC
# MAGIC
# MAGIC # Create tar file
# MAGIC echo "Creating tar file..."
# MAGIC cd dependencies 
# MAGIC tar cvfz dependencies.tar.gz packages/
# MAGIC echo "Tar file created successfully at /databricks/driver/dependencies/dependencies.tar.gz"
# MAGIC
# MAGIC echo "Download dependecies script finished successfully."

# COMMAND ----------

# DBTITLE 1,Copy dependencies.tar.gz to dbfs
# MAGIC %sh
# MAGIC # Define the path of the tar file
# MAGIC LOCAL_PACKAGES_PATH="/dbfs/FileStore/packages"
# MAGIC TAR_FILE="$LOCAL_PACKAGES_PATH/dependencies.tar.gz"
# MAGIC
# MAGIC # Remove the old packages directory if it exists
# MAGIC if [ -d "$LOCAL_PACKAGES_PATH/packages" ]; then
# MAGIC   echo "Removing previous packages directory"
# MAGIC   rm -rf "$LOCAL_PACKAGES_PATH/packages"
# MAGIC fi
# MAGIC
# MAGIC # Create directory /dbfs/FileStore/packages if it doesn't exist
# MAGIC if [ ! -d "$LOCAL_PACKAGES_PATH" ]; then
# MAGIC   mkdir -p "$LOCAL_PACKAGES_PATH"
# MAGIC fi
# MAGIC
# MAGIC # Check if tar file exists
# MAGIC if [ ! -f "/databricks/driver/dependencies/dependencies.tar.gz" ]; then
# MAGIC   echo "Tar file not found." 
# MAGIC   exit 1
# MAGIC fi
# MAGIC
# MAGIC # Copy file from /databricks/driver to /dbfs/FileStore/packages
# MAGIC echo "Copying dependencies to $LOCAL_PACKAGES_PATH"
# MAGIC cp /databricks/driver/dependencies/dependencies.tar.gz "$LOCAL_PACKAGES_PATH"
# MAGIC
# MAGIC # Verify that file was copied successfully
# MAGIC if [ -f "$LOCAL_PACKAGES_PATH/dependencies.tar.gz" ]; then
# MAGIC   echo "File copied successfully."
# MAGIC else
# MAGIC   echo "File could not be copied."
# MAGIC fi
# MAGIC
# MAGIC # Extract contents of tar file to destination directory
# MAGIC echo "Extracting contents of $TAR_FILE to $LOCAL_PACKAGES_PATH"
# MAGIC if ! tar -xzf "$TAR_FILE" -C "$LOCAL_PACKAGES_PATH"; then
# MAGIC   echo "Failed to extract contents of $TAR_FILE to $LOCAL_PACKAGES_PATH"
# MAGIC   exit 1
# MAGIC fi
# MAGIC
# MAGIC #
# MAGIC ## Move .tar.gz files to a separate directory
# MAGIC #echo "Moving .tar.gz files to /dbfs/FileStore/packages/tars"
# MAGIC #if [ ! -d "$LOCAL_PACKAGES_PATH/tars" ]; then
# MAGIC #  mkdir -p "$LOCAL_PACKAGES_PATH/tars"
# MAGIC #fi
# MAGIC #
# MAGIC ## Check if packages directory exists before moving .tar.gz files
# MAGIC #if [ -d "$LOCAL_PACKAGES_PATH/packages" ]; then
# MAGIC #  mv "$LOCAL_PACKAGES_PATH/packages/"*.tar.gz "$LOCAL_PACKAGES_PATH/tars/"
# MAGIC #fi
# MAGIC
# MAGIC echo "Libraries copied successfully."

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Step 2: Create Init Script
# MAGIC
# MAGIC To make the dependencies available for all the participants, we need to create an init script. This init script will access the unpacked dependencies.tar.gz in **/dbfs/FileStore/packages/packages/** path and install the specified dependencies from there. 

# COMMAND ----------

# DBTITLE 1,Create init script and put in dbfs
dbutils.fs.mkdirs("dbfs:/databricks/init_scripts/")
dbutils.fs.put("dbfs:/databricks/init_scripts/llm_hackathon_dolly_dependencies.sh", """
#!/bin/bash

# Define the path of the tar file
LOCAL_PACKAGES_PATH="/dbfs/FileStore/packages/packages/"

echo "Upgrade dependencies required for hackathon"
pip install --no-build-isolation --no-index numba mleap --upgrade --find-links $LOCAL_PACKAGES_PATH

echo "Installing dependencies required for hackathon"
pip install --no-build-isolation --no-index chromadb==0.3.22 --find-links $LOCAL_PACKAGES_PATH

""", True)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Step 3: Cluster configuration for participants.
# MAGIC
# MAGIC The cluster configuration bewlow can be used to create clusters for the participants. We use Databricks runtime 13.2 ML GPU for the hackathon and also point to the init script. Please add the participants name to the configuration.
# MAGIC

# COMMAND ----------

# DBTITLE 1,Cluster configuration for participants
# MAGIC %md
# MAGIC
# MAGIC
# MAGIC ```json
# MAGIC {
# MAGIC     "num_workers": 0,
# MAGIC     "cluster_name": "dbdemos-llm-dolly-chatbot-<add-user-name-here>",
# MAGIC     "spark_version": "13.2.x-gpu-ml-scala2.12",
# MAGIC     "spark_conf": {
# MAGIC         "spark.databricks.dataLineage.enabled": "true",
# MAGIC         "spark.databricks.cluster.profile": "singleNode",
# MAGIC         "spark.master": "local[*, 4]",
# MAGIC         "spark.databricks.delta.preview.enabled": "true"
# MAGIC     },
# MAGIC     "azure_attributes": {
# MAGIC         "first_on_demand": 1,
# MAGIC         "availability": "ON_DEMAND_AZURE",
# MAGIC         "spot_bid_max_price": -1
# MAGIC     },
# MAGIC     "node_type_id": "Standard_NC6s_v3",
# MAGIC     "driver_node_type_id": "Standard_NC6s_v3",
# MAGIC     "ssh_public_keys": [],
# MAGIC     "custom_tags": {
# MAGIC         "project": "dbdemos",
# MAGIC         "demo": "llm-dolly-chatbot",
# MAGIC         "ResourceClass": "SingleNode"
# MAGIC     },
# MAGIC     "cluster_log_conf": {
# MAGIC         "dbfs": {
# MAGIC             "destination": "dbfs:/FileStore/packages/cluster-logs"
# MAGIC         }
# MAGIC     },
# MAGIC     "spark_env_vars": {},
# MAGIC     "autotermination_minutes": 60,
# MAGIC     "enable_elastic_disk": true,
# MAGIC     "cluster_source": "API",
# MAGIC     "init_scripts": [
# MAGIC         {
# MAGIC             "dbfs": {
# MAGIC                 "destination": "dbfs:/databricks/init_scripts/llm_hackathon_dolly_dependencies.sh"
# MAGIC             }
# MAGIC         }
# MAGIC     ],
# MAGIC     "enable_local_disk_encryption": false,
# MAGIC     "data_security_mode": "NONE",
# MAGIC     "runtime_engine": "STANDARD"
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Step 3: Download models

# COMMAND ----------

# MAGIC %pip install -U transformers==4.29.0

# COMMAND ----------

import os
os.environ["HF_DATASETS_OFFLINE"] = "1" 
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# COMMAND ----------

# DBTITLE 1,Download embedding model from huggingface an put into dbfs
from sentence_transformers import SentenceTransformer

# Set dbfs path 
modelPath = "/dbfs/FileStore/cs_hackathon/sentence-transformer/all-mpnet-base-v2"

# Load SentenceTransformer and put in dbfs 
model = SentenceTransformer('all-mpnet-base-v2')
model.save(modelPath)

# COMMAND ----------

# DBTITLE 1,Download Instruction following Dolly LLM
from transformers import pipeline
import torch

# Specify model name
model_name = "databricks/dolly-v2-3b" 

# Create pipeline model 
instruct_pipeline = pipeline(model=model_name)

# Put model into dbfs 
instruct_pipeline.save_pretrained("/dbfs/FileStore/cs_hackathon/instruction/dolly-v2-3b")

# COMMAND ----------

# DBTITLE 1,Download summarize model t5-small
from transformers import pipeline

# Specify model name
model_name = "t5-small" 
  
# Create pipeline model 
instruct_pipeline = pipeline(model=model_name)

# Put model into dbfs 
instruct_pipeline.save_pretrained("/dbfs/FileStore/cs_hackathon/instruction/t5-small")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Step 4: Download sample data
# MAGIC
# MAGIC This repo also contains a parquet file. Execute the cell below to put the file into the dbfs file system where it can be found by the participants. 

# COMMAND ----------

# DBTITLE 1,Copy data from local path into dbfs file system
import os

current_user_name = "andreas.jack@databricks.com"

# Specify local file path
local_file_path = f"/Workspace/Users/{current_user_name}/LLMHackathon/Admin/Data/gardening.snappy.parquet"

# Specify destination on DBFS (Note the initial slash and '/Workspace/')
dbfs_destination = f"/dbdemos/product/llm/gardening/data/gardening.snappy.parquet"

# Copy local file to DBFS
dbutils.fs.cp("file://" + local_file_path, "dbfs:" + dbfs_destination)

# COMMAND ----------

# DBTITLE 1,Check if the data is at the expected place
# MAGIC %fs ls /dbdemos/product/llm/gardening/data

# COMMAND ----------


