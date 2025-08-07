import streamlit as st
import pandas as pd
import boto3

from io import StringIO

from utils.folder_manager import create_client_entry, check_client_entry
from utils.invoke_lambda_function import invoke_lambda_function

def main():
    st.title("KYC Intelligent Agent Management")

    # Get client ID from user input
    client_id = st.text_input("Enter Client ID:")
    st.session_state.client_entry = None
    st.session_state.df_clnt_info = None
    
    if st.button("Create New Case"):
        if client_id:
            is_new_case, client_entry = create_client_entry(str(client_id))  
            if is_new_case:
                st.success(f"New case for client '{client_id}' created successfully!")
            else:
                st.error(f"New case for client '{client_id}' already exists or could not be created.")
        else:
            st.error("Please enter a valid Client ID.")
        st.session_state.client_entry = client_entry
    
    # Check if client entry exists 
    if st.button("Check Client ID"):
        if client_id:
            is_new_case, client_entry = check_client_entry(str(client_id))
            if is_new_case:
                st.error(f"The client for '{client_id}' does not exist.")
            else:
                st.success(f"The client for '{client_id}' exists.")
        else:
            st.error("Please enter a valid Client ID.")
        st.session_state.client_entry. = client_entry
        st.dataframe(client_entry)
    
    if st.button("Run Data Processing"):
        if client_id:
            with st.spinner("Running Data Processing..."):
                payload = {'CLNT_NBR': client_id}
                internal_data_bucket = "internaldataprocess"
                internal_data_object = "real_cu_list.csv"

                # Initialize S3 client
                s3 = boto3.client('s3')

                # Download CSV from S3
                response = s3.get_object(Bucket=internal_data_bucket, Key=internal_data_object)
                csv_content = response['Body'].read().decode('utf-8')
                df = pd.read_csv(StringIO(csv_content), skiprows=10)
                df_clnt_info = df[df['CU Number'].astype(str) == str(client_id)]
            st.session_state.df_clnt_info = df_clnt_info
            st.dataframe(df_clnt_info)
                
        else:
            st.error("This client ID does not exist. Please create a new case first.")
    print('Session_state:\n', st.session_state)
    if st.button("Run StreetView Agent"):
        if client_entry['Proc1'].isnull():
            with st.spinner("Running AI agents..."):
                payload = {'CLNT_NBR': df_clnt_info['CU Number'], 
                           'ADDRESS': df_clnt_info['Employer Address']}
                response = invoke_lambda_function("street_view", payload=payload)

                if response['statusCode'] == 200:
                    streetview_bucket = response['bucket']
                    streetview_object = response['image_name']

                    st.success("StreetView Agent completed successfully!")
                    client_entry['Proc1'] = 'Completed'
                    client_entry['Proc1_Bucket'] = streetview_bucket
                    client_entry['Proc1_Object'] = streetview_object
                else:
                    st.error("StreetView Agent failed to run.")
            
        else:
            st.error("This client has already been processed by the StreetView Agent.")

    if st.button("Run Webscraping Agent"):
        if client_entry['Proc3'] is None:
            with st.spinner("Running AI agents..."):
                payload = {'CLNT_NBR': client_id, 
                           'Proc1_Bucket': client_entry['Proc1_Bucket'], 'Proc1_Object': client_entry['Proc1_Object'],
                           'Proc2_Bucket': client_entry['Proc2_Bucket'], 'Proc2_Object': client_entry['Proc2_Object']}
                response = invoke_lambda_function("ExternalDataAgent", payload=payload)

                if response['statusCode'] == 200:
                    external_data_bucket = response['bucket']
                    external_data_object = response['object_key']

                    st.success("External Data Agent completed successfully!")
                    client_entry['Proc3'] = 'Completed'
                    client_entry['Proc3_Bucket'] = external_data_bucket
                    client_entry['Proc3_Object'] = external_data_object
                else:
                    st.error("Webscraping Agent failed to run.")
        else:
            st.error("This client has already been processed by the External Data Agent.")
if __name__ == "__main__":
    main()