# pip install pandas numpy google-cloud-bigquery db-dtypes
# Ensure you are authenticated with GCP: gcloud auth application-default login
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from google.cloud import bigquery

# ==========================================
# 1. CONFIGURATION
# ==========================================
PROJECT_ID = 'harborisland-dev'  # REPLACE WITH YOUR GCP PROJECT ID
DATASET_ID = 'opendoor_demo'        # The BigQuery dataset (create this in BQ first)
TABLE_ID = 'housing_acquisitions'   # The target table name
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# Data generation parameters
START_DATE = datetime(2023, 3, 25)
DAYS = 1460 # 4 years of daily data
ZIP_CODES = ['85001', '85002', '85003'] # Target expansion metros (e.g., Phoenix area)

# ==========================================
# 2. GENERATE SYNTHETIC TIME-SERIES DATA
# ==========================================
print("Generating synthetic housing data...")

records = []
for zip_code in ZIP_CODES:
    # Set a base baseline for each zip code to make them look distinct
    base_homes = np.random.randint(5, 15)
    base_dom = np.random.randint(30, 60) # Days on market
    base_price = np.random.randint(350000, 600000)

    for i in range(DAYS):
        current_date = START_DATE + timedelta(days=i)
        
        # Add some seasonality (higher in summer, lower in winter)
        day_of_year = current_date.timetuple().tm_yday
        seasonality = np.sin(2 * np.pi * day_of_year / 365) 
        
        # Calculate daily values with noise and seasonality
        homes_acquired = max(0, int(base_homes + (seasonality * 3) + np.random.normal(0, 2)))
        avg_dom = max(10, int(base_dom - (seasonality * 10) + np.random.normal(0, 5)))
        avg_purchase_price = max(100000, round(base_price + (seasonality * 20000) + np.random.normal(0, 15000), 2))
        
        records.append({
            'transaction_date': current_date.date(),
            'zip_code': zip_code,
            'homes_acquired': homes_acquired,
            'avg_days_on_market': avg_dom,
            'avg_purchase_price': avg_purchase_price
        })

# Create DataFrame
df = pd.DataFrame(records)
print(f"Generated {len(df)} rows of data.")
print(df.head())

# ==========================================
# 3. UPLOAD TO BIGQUERY
# ==========================================
print(f"\nUploading data to BigQuery table: {FULL_TABLE_ID}...")

# Initialize BigQuery Client
client = bigquery.Client(project=PROJECT_ID)

# Create Dataset if it does not exist ---
dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
dataset = bigquery.Dataset(dataset_ref)
dataset.location = "US" # You can change this to your preferred GCP region

# exists_ok=True ensures it won't throw an error if the dataset is already there
dataset = client.create_dataset(dataset, exists_ok=True)
print(f"Dataset {dataset.dataset_id} is ready.")

# Define Job Config (Schema and Write Disposition)
job_config = bigquery.LoadJobConfig(
    schema=[
        bigquery.SchemaField("transaction_date", "DATE"),
        bigquery.SchemaField("zip_code", "STRING"),
        bigquery.SchemaField("homes_acquired", "INTEGER"),
        bigquery.SchemaField("avg_days_on_market", "INTEGER"),
        bigquery.SchemaField("avg_purchase_price", "FLOAT"),
    ],
    write_disposition="WRITE_TRUNCATE", # Overwrites table if it already exists
)

# Load the dataframe into BigQuery
job = client.load_table_from_dataframe(
    df, FULL_TABLE_ID, job_config=job_config
)

# Wait for the job to complete
job.result() 

# Validate loading
table = client.get_table(FULL_TABLE_ID)
print(f"Success! Loaded {table.num_rows} rows and {len(table.schema)} columns to {FULL_TABLE_ID}")