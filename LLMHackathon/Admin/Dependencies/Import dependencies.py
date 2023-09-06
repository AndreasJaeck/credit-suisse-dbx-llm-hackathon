# Databricks notebook source
# MAGIC %md
# MAGIC To import the require hackathon dependecnies follow these steps:
# MAGIC
# MAGIC Step 1: 
# MAGIC - In this folder there is a dependencies.tar.gz. Put this file in the dbfs path: **/dbfs/FileStore/packages/**
# MAGIC
# MAGIC Step 2: 
# MAGIC - Excecute the cell below to unpack the dependencies. Now the dependencies can be used with an init script that 

# COMMAND ----------

# DBTITLE 1,Unpack dependencies.tar.gz
# MAGIC %sh
# MAGIC
# MAGIC LOCAL_PACKAGES_PATH="/dbfs/FileStore/packages"
# MAGIC TAR_FILE="$LOCAL_PACKAGES_PATH/dependencies.tar.gz"
# MAGIC
# MAGIC # Extract contents of tar file to destination directory
# MAGIC echo "Extracting contents of $TAR_FILE to $LOCAL_PACKAGES_PATH"
# MAGIC if ! tar -xzf "$TAR_FILE" -C "$LOCAL_PACKAGES_PATH"; then
# MAGIC   echo "Failed to extract contents of $TAR_FILE to $LOCAL_PACKAGES_PATH"
# MAGIC   exit 1
# MAGIC fi
