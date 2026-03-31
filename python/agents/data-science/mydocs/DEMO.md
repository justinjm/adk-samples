# DEMO

Sample questions for running a demo of the data science agent.

* Hi, What data do you have access to?
* I need more details on the train table. What countries exist? How many stores are there?
* Generate a plot with total sales per country of the train table
* What kinds of forecasting models can I train in BQML?
* Can you train an ARIMA_PLUS model that forecasts total sales (num_sold) by date from the train table?
* Using the BQML model you just trained, can you use BQML to generate a forecast of total sales for 30 days and visualize the results as a time series plot? include the upper and lower prediction interval bounds in the plot


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