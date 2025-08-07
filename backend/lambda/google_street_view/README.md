# Google Street View Image Extraction  
This function is to extract the street view image of customer's company address.  
It is triggered by a button event in streamlit user-interface.  

**Lambda Function URL**: <https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/street_view?tab=code>  

**Environment Variables / Parameters**:    
   <!-- * ADD_SRC_S3_BUCKET : string, S3 bucket for database of customer data  -->
   * GM_API_KEY : string, Personal Google Geocoding API  
   * IMAGE_S3_BUCKET : string, S3 bucket for storing the street view image  
   <!-- * SRC_FILE_NAME : string, S3 bucket for file name of customer data ADD_SRC_S3_BUCKET  -->


**Parameters**:  
   * event : dict, input data from the event  
   * context : dict, context information about the Lambda function execution environment  
      * **Parameters for event json**:   
      * CLNT_NBR : string, a customer number  
      * ADDRRESS : string, customer's company address  
          
**Return**:  
   * statusCode : integer, status code   
   * body : string, result statement  
   * address : address, customer address  
   * bucket : img_bucket_name, S3 bucket name for storing images  
   * image_name : .jpg, a street view image of customer's employer company address

## Sample  
**Event json**
```
{  
   "CLNT_NBR" : "123456704",  
   "ADDRESS" : "270 Park Avenue,. New York City. ,. United States"  
}
```

**Street view image captured from Google Map**
