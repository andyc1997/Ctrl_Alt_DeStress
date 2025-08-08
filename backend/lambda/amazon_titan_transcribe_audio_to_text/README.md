# Transcribe - Amazon Titan Text Express v1  
This function is to transcribe the audio call log from the calling conversation between customer and relationship manager to a .json.  
It is triggered by a button event in streamlit user-interface.  

**Lambda Function URL**: <https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/rmcall?tab=code>  

**Return**:  
   * statusCode : integer, status code   
   * body : dict, processed results  
   * .json : a .json of processed speech result based on audio input  
