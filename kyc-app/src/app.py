import streamlit as st
import os
import requests
import boto3

from utils.folder_manager import create_client_entry, check_client_entry
from utils.invoke_lambda_function import invoke_lambda_function

def main():
    st.title("KYC Intelligent Agent Management")

    # Get client ID from user input
    client_id = st.text_input("Enter Client ID:")
    
    if st.button("Create New Case"):
        if client_id:
            is_new_case, client_entry = create_client_entry(str(client_id))  
            if is_new_case:
                st.success(f"Folder for client '{client_id}' created successfully!")
            else:
                st.error(f"Folder for client '{client_id}' already exists or could not be created.")
        else:
            st.error("Please enter a valid Client ID.")
    
    # Check if client entry exists 
    if st.button("Check Client Entry"):
        if client_id:
            is_new_case, client_entry = check_client_entry(str(client_id))
            if is_new_case:
                st.error(f"Client entry for '{client_id}' does not exist.")
            else:
                st.success(f"Client entry for '{client_id}' exists.")
        else:
            st.error("Please enter a valid Client ID.")
    
    if st.button("Run Data Processing Agent"):
        if client_entry['Proc1'] is None:
            with st.spinner("Running AI agents..."):
                payload = {'CLNT_NBR': client_id}
                response = invoke_lambda_function("TextractToCSV", payload=payload)

                if response['statusCode'] == 200:
                    data_processing_bucket = response['bucket']
                    data_processing_object = response['object_key']

                    st.success("Data Processing Agent completed successfully!")
                    client_entry['Proc1'] = 'Completed'
                    client_entry['Proc1_Bucket'] = data_processing_bucket
                    client_entry['Proc1_Object'] = data_processing_object
                else:
                    st.error("Data Processing Agent failed to run.")
        else:
            st.error("This client has already been processed by the Data Processing Agent.")
        
    if st.button("Run StreetView Agent"):
        if client_entry['Proc2'] is None:
            with st.spinner("Running AI agents..."):
                payload = {'CLNT_NBR': client_id, 'Proc1_Bucket': client_entry['Proc1_Bucket'], 'Proc1_Object': client_entry['Proc1_Object']}
                response = invoke_lambda_function("street_view", payload=payload)

                if response['statusCode'] == 200:
                    streetview_bucket = response['bucket']
                    streetview_object = response['image_name']

                    st.success("Data Processing Agent completed successfully!")
                    client_entry['Proc2'] = 'Completed'
                    client_entry['Proc2_Bucket'] = streetview_bucket
                    client_entry['Proc2_Object'] = streetview_object
                else:
                    st.error("StreetView Agent failed to run.")
        else:
            st.error("This client has already been processed by the StreetView Agent.")

if __name__ == "__main__":
    main()