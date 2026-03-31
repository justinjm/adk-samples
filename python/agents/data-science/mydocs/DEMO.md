# DEMO

## housing acquistions 

* hi what data can you access?
* I need to analyze our recent housing acquisition data. what is the distribution of homes purchased by zip code? and can you also generate a plot for me to visualize?
* Can you train an ARIMA_PLUS model in BigQuery ML to forecast the number of days on market for homes in the 85001 zip code from the `housing_acquisitions` table? (Use the zip_code as time_series_id_col)
* Using the model you just trained, can you generate a time series plot of a forecast for 30 days? and include the upper and lower prediction interval bounds?
* **Bonus:** generate a time series plot of an actual and forecast using a joined datasset of  actuals from `housing_acquisitions` table and forecast from `example_forecast` table. include upper and lower prediction interval bounds for the forecast period. 


example successful query:

```sql
CREATE OR REPLACE MODEL `harborisland-dev.opendoor_demo.arima_plus_model`
OPTIONS(
  model_type='ARIMA_PLUS',
  time_series_timestamp_col='transaction_date',
  time_series_data_col='avg_days_on_market',
  time_series_id_col='zip_code'
) AS
SELECT
  transaction_date,
  avg_days_on_market,
  zip_code
FROM
  `harborisland-dev.opendoor_demo.housing_acquisitions`
WHERE
  zip_code = '85001'
```


## sticker sales 

Sample questions for running a demo of the data science agent.

* Hi, What data do you have access to?
* I need more details on the train table. What countries exist? How many stores are there?
* Generate a plot with total sales per country of the train table
* What kinds of forecasting models can I train in BQML?
* Can you train an ARIMA_PLUS model that forecasts total sales (sum of  num_sold) by date from the train table?
* Using the model you just trained, generate a forecast of total sales for 30 days and visualize the results as a time series plot. include the upper and lower prediction interval bounds in the plot



```sql
SELECT 
    forecast_timestamp, 
    forecast_value, 
    prediction_interval_lower_bound, 
    prediction_interval_upper_bound 
FROM 
    ML.FORECAST(
        MODEL `harborisland-dev.opendoor_demo.arima_plus_model`, 
        STRUCT(30 AS horizon, 0.95 AS confidence_level)
    )
```

