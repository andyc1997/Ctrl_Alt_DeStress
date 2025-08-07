# Amazon Titan Text Express v1  
This function is to web scrape customer's working background based on customer name, company name, company address.  
It is triggered by a button event in streamlit user-interface.  

**Lambda Function URL**: <[https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/street_view?tab=code](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/externaldataprocesscode?tab=code)>  

**Environment Variables / Parameters**:    
   <!-- * ADD_SRC_S3_BUCKET : string, S3 bucket for database of customer data  -->
   * FUNC_S3_BUCKET : string, S3 bucket for storing the scraping result
   * GOOGLE_API_KEY : string, Personal Google Geocoding API
   * GOOGLE_CSE_ID : string, Personal Google CSE ID
   <!-- * SRC_FILE_NAME : string, S3 bucket for file name of customer data ADD_SRC_S3_BUCKET  -->


**Parameters**:  
   * event : dict, input data from the event  
   * context : dict, context information about the Lambda function execution environment  
      * **Parameters for event json**:   
      * CLNT_NBR : string, a customer number
      * CUSTOMER_NAME : string, customer name
      * OCCUPATION : string, customer's occupation
      * COMPANY : string, customer's company name
      * LOCATION : string, customer's company location  
          
**Return**:  
   * statusCode : integer, status code   
   * body : string, result statement  
   * customer_name : string, customer_name,
   * url_statements : string, url_statements,google-search-credentials
   * bucket : string, bucket_name
   * s3_key : .json, a .json of scraped content

## Sample  
**Event json**
```
{
  "CLNT_NBR" : "123456704",
  "CUSTOMER_NAME" : "Jamie Dimon",
  "OCCUPATION" : "CEO",
  "COMPANY" : "JPMorgan Chase & Co.",
  "LOCATION" : "270 Park Avenue,. New York City. ,. United States"
}
```


