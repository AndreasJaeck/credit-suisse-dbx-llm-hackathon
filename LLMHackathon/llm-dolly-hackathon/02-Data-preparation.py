# Databricks notebook source
# MAGIC %md 
# MAGIC ### For this hackathon cluster will be generated for you 
# MAGIC To run this demo, just select the cluster `dbdemos-llm-dolly-chatbot-user-name` from the dropdown menu ([open cluster configuration](https://adb-984752964297111.11.azuredatabricks.net/#setting/clusters/0830-144024-wxydlwo/configuration)). <br />
# MAGIC *Note: If the cluster was deleted after 30 days, you can re-create it with `dbdemos.create_cluster('llm-dolly-chatbot')` or re-install the demo: `dbdemos.install('llm-dolly-chatbot')`*

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC # Dolly: data Preparation & Vector database creation with Databricks Lakehouse
# MAGIC
# MAGIC <img style="float: right" width="600px" src="https://raw.githubusercontent.com/databricks-demos/dbdemos-resources/main/images/product/llm-dolly/llm-dolly-data-prep-small.png">
# MAGIC
# MAGIC To be able to specialize our model, we need a list of Q&A that we'll use as training dataset.
# MAGIC
# MAGIC For this demo, we'll specialize our model using Stack Exchange dataset. 
# MAGIC
# MAGIC Let's start with a simple data pipeline ingesting the Stack Exchange dataset, running some cleanup & saving it for further training.
# MAGIC
# MAGIC We will implement the following steps: <br><br>
# MAGIC
# MAGIC <style>
# MAGIC .right_box{
# MAGIC   margin: 30px; box-shadow: 10px -10px #CCC; width:650px; height:300px; background-color: #1b3139ff; box-shadow:  0 0 10px  rgba(0,0,0,0.6);
# MAGIC   border-radius:25px;font-size: 35px; float: left; padding: 20px; color: #f9f7f4; }
# MAGIC .badge {
# MAGIC   clear: left; float: left; height: 30px; width: 30px;  display: table-cell; vertical-align: middle; border-radius: 50%; background: #fcba33ff; text-align: center; color: white; margin-right: 10px; margin-left: -35px;}
# MAGIC .badge_b { 
# MAGIC   margin-left: 25px; min-height: 32px;}
# MAGIC </style>
# MAGIC
# MAGIC
# MAGIC <div style="margin-left: 20px">
# MAGIC   <div class="badge_b"><div class="badge">1</div> Download raw Q&A dataset</div>
# MAGIC   <div class="badge_b"><div class="badge">2</div> Clean & prepare our gardenig questions and best answers</div>
# MAGIC   <div class="badge_b"><div class="badge">3</div> Use a Sentence 2 Vect model to transform our docs in a vector</div>
# MAGIC   <div class="badge_b"><div class="badge">4</div> Index the vector in our Vector database (Chroma)</div>
# MAGIC </div>
# MAGIC <br/>
# MAGIC
# MAGIC <!-- Collect usage data (view). Remove it to disable collection. View README for more details.  -->
# MAGIC <img width="1px" src="https://www.google-analytics.com/collect?v=1&gtm=GTM-NKQ8TT7&tid=UA-163989034-1&aip=1&t=event&ec=dbdemos&ea=VIEW&dp=%2F_dbdemos%2Fdata-science%2Fllm-dolly-chatbot%2F02-Data-preparation&cid=984752964297111&uid=1814403842957890">

# COMMAND ----------

# MAGIC %run ./_resources/00-init $catalog=hive_metastore $db=dbdemos_llm

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1/ Get the raw dataset
# MAGIC
# MAGIC This dataset is already in the local file system. Please run the code bewlo

# COMMAND ----------

# DBTITLE 1,Our Q&A dataset is ready
# MAGIC %fs ls /dbdemos/product/llm/gardening/data

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## 2/ Clean & prepare our gardenig questions and best answers 
# MAGIC
# MAGIC We will perform some light preprocessing on the results:
# MAGIC - Keep only questions/answers with a reasonable score
# MAGIC - Parse HTML into plain text
# MAGIC - Join questions and answers to form question-answer pairs
# MAGIC
# MAGIC *Note that this pipeline is basic. For more advanced ingestion examples with Databricks Lakehouse, try Delta Live Tables: `dbdemos.instal('dlt_loan')`*

# COMMAND ----------

# DBTITLE 1,Review our raw Q&A dataset
gardening_raw_path = demo_path+"/gardening/data/"

raw_gardening = spark.read.parquet(gardening_raw_path)
display(raw_gardening)

# COMMAND ----------

from bs4 import BeautifulSoup

#UDF to transform html content as text
@pandas_udf("string")
def html_to_text(html):
  return html.apply(lambda x: BeautifulSoup(x).get_text())

# Create gardening df
#   1. keep only records with score >= 5
#   2. convert html body to text
#   3. Remove questions that have len(body) > 1000
#   4. Rename _Id to id and _ParentId to parent_id
#   5. Select id, body and parent_if columns 
# <write code here>

gardening_df =(raw_gardening
                  .# <write code here>
                  .# <write code here>
                  .withColumn("body", html_to_text("_Body")) #Convert html to text
                  .# <write code here>
                  .# <write code here>)


# Save 'raw' content for later loading of questions
gardening_df.write.mode("overwrite").saveAsTable(f"gardening_dataset")
display(spark.table("gardening_dataset"))

# COMMAND ----------

# DBTITLE 1,Assemble questions and answers
gardening_df = spark.table("gardening_dataset")

# Self-join to assemble questions and answers
qa_df = gardening_df.alias("a").filter("parent_id IS NULL") \
          .join(gardening_df.alias("b"), on=[col("a.id") == col("b.parent_id")]) \
          .select("b.id", "a.body", "b.body") \
          .toDF("answer_id", "question", "answer")
          
# Prepare the training dataset: question following with the best answers.
docs_df = qa_df.select(col("answer_id"), F.concat(col("question"), F.lit("\n\n"), col("answer"))).toDF("source", "text")
display(docs_df)

# COMMAND ----------

# DBTITLE 1,Write data to delta table
# Write data to delta table 
docs_df.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(f"gardening_training_dataset")
display(spark.table("gardening_training_dataset"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3/ Load our model to transform our docs to embeddings
# MAGIC
# MAGIC We will simply load a sentence to an embedding model from Hugging Face and use it later in the chromadb client.

# COMMAND ----------

from langchain.embeddings import HuggingFaceEmbeddings

# Load embedding model from dbfs
modelPath = "/dbfs/FileStore/cs_hackathon/sentence-transformers/all-mpnet-base-v2"
hf_embed = HuggingFaceEmbeddings(model_name=modelPath)


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## 4/ Index the documents (rows) in our vector database
# MAGIC
# MAGIC Now it's time to load the texts that have been generated, and create a searchable database of text for use in the `langchain` pipeline. <br>
# MAGIC These documents are embedded, so that later queries can be embedded too, and matched to relevant text chunks by embedding.
# MAGIC
# MAGIC - Collect the text chunks with Spark; `langchain` also supports reading chunks directly from Word docs, GDrive, PDFs, etc.
# MAGIC - Create a simple in-memory Chroma vector DB for storage
# MAGIC - Instantiate an embedding function from `sentence-transformers`
# MAGIC - Populate the database and save it

# COMMAND ----------

# DBTITLE 1,Prepare our database storage location (in dbfs)
# Prepare a directory to store the document database. Any path on `/dbfs` will do.
dbutils.widgets.dropdown("reset_vector_database", "false", ["false", "true"], "Recompute embeddings for chromadb")
gardening_vector_db_path = demo_path+"/vector_db"

# Don't recompute the embeddings if the're already available
compute_embeddings = dbutils.widgets.get("reset_vector_database") == "true" or is_folder_empty(gardening_vector_db_path)

if compute_embeddings:
  print(f"creating folder {gardening_vector_db_path} under our blob storage (dbfs)")
  dbutils.fs.rm(gardening_vector_db_path, True)
  dbutils.fs.mkdirs(gardening_vector_db_path)

# COMMAND ----------

# MAGIC %md
# MAGIC Create the document database:
# MAGIC - Just collect the relatively small dataset of text and form `Document`s; `langchain` can also form doc collections directly from PDFs, GDrive files, etc
# MAGIC - Split long texts into manageable chunks

# COMMAND ----------

from langchain.docstore.document import Document
from langchain.vectorstores import Chroma

all_texts = spark.table("gardening_training_dataset")

print(f"Saving document embeddings under /dbfs{gardening_vector_db_path}")

if compute_embeddings: 
  # Transform our rows as langchain Documents
  # If you want to index shorter term, use the text_short field instead
  documents = [Document(page_content=r["text"], metadata={"source": r["source"]}) for r in all_texts.collect()]

  # If your texts are long, you may need to split them. However it's best to summarize them instead as show above.
  text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=100)
  documents = text_splitter.split_documents(documents)

  # Init the chroma db with the sentence-transformers/all-mpnet-base-v2 model loaded from hugging face  (hf_embed)
  db = Chroma.from_documents(collection_name="gardening_docs", documents=documents, embedding=hf_embed, persist_directory="/dbfs"+gardening_vector_db_path)
  db.similarity_search("dummy") # tickle it to persist metadata (?)
  db.persist()

# COMMAND ----------

# Make sure you restart the python kernel to free our gpu memory if you're using multiple notebooks0
# (load the model only once in 1 single notebook to avoid OOM)
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ## That's it, our Q&A dataset is ready.
# MAGIC
# MAGIC In this notebook, we leverage Databricks to prepare our Q&A dataset:
# MAGIC
# MAGIC * Ingesting & cleaning our dataset
# MAGIC * Preparing our embeddings and saving them in chroma
# MAGIC
# MAGIC We're now ready to use this dataset to improve our prompt context and build our Gardening Chat Bot! 
# MAGIC Open the next notebook [03-Q&A-prompt-engineering-for-dolly]($./03-Q&A-prompt-engineering-for-dolly)
