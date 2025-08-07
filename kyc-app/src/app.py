import streamlit as st
import pandas as pd
import boto3

from io import StringIO
from utils.folder_manager import create_client_entry, check_client_entry, get_client_entry
from utils.invoke_lambda_function import invoke_lambda_function
from utils.invoke_s3 import s3_read_csv, s3_write_csv

def main():
    st.title("KYC Intelligent Agent Management")

    # Get client ID from user input
    client_id = st.text_input("Enter Client ID:")
    s3 = boto3.client('s3')

    # Get entry details
    entry_bucket_name = 'client-master-entry'
    entry_object_key = 'clnt_master_entry.csv'

    # Initialize session state variables
    if 'client_entry' not in st.session_state:
        st.session_state.client_entry = None
    if 'df_clnt_info' not in st.session_state:
        st.session_state.df_clnt_info = None
    if 'df_entry_table' not in st.session_state:
        st.session_state.df_entry_table = None
    else: 
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)

    # Create New Case
    # if st.button("Create New Case"):
    #     if client_id and len(str(client_id)) == 9:
    #         is_new_case, client_entry = create_client_entry(str(client_id), entry_bucket_name, entry_object_key)  
    #         if is_new_case:
    #             st.success(f"New case for client '{client_id}' created successfully!")
    #         else:
    #             st.info(f"New case for client '{client_id}' already exists or could not be created.")
    #         st.session_state.client_entry = client_entry.iloc[0].to_dict()
    #         st.dataframe(client_entry)
    #     else:
    #         st.info("Please enter a valid Client ID.")
    
    # Check if client entry exists 
    if st.button("Check Client ID"):
        if client_id and len(str(client_id)) == 9:
            is_new_case, client_entry = check_client_entry(str(client_id), entry_bucket_name, entry_object_key)
            if is_new_case:
                st.info(f"The client for '{client_id}' does not exist.")
            else:
                st.success(f"The client for '{client_id}' exists.")
                st.session_state.client_entry = client_entry.iloc[0].to_dict()
                st.dataframe(client_entry) # Display client entry details
        else:
            st.info("Please enter a valid Client ID.")
    
    # Read internal database
    if st.button("Run Data Processing"):
        if client_id:
            with st.spinner("Running Data Processing..."):
                internal_data_bucket = "internaldataprocess"
                internal_data_object = "real_cu_list.csv"
                df = s3_read_csv(s3, internal_data_bucket, internal_data_object, skiprows=10)
                df_clnt_info = get_client_entry(df, str(client_id), 'CU Number')
            st.session_state.df_clnt_info = df_clnt_info.iloc[0].to_dict()
            st.dataframe(df_clnt_info)                
        else:
            st.info("This client ID does not exist. Please create a new case first.")

    # Run StreetView agent
    if st.button("Run StreetView Agent"):
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)
        if pd.isna(st.session_state.client_entry['Proc1']):
            with st.spinner("Running AI agents..."):
                payload = {
                    'CLNT_NBR': st.session_state.df_clnt_info['CU Number'], 
                    'ADDRESS': st.session_state.df_clnt_info['Employer Address']
                }
                response = invoke_lambda_function("street_view", payload=payload)
                if response['statusCode'] == 200:
                    # get response
                    streetview_bucket = response['bucket']
                    streetview_object = response['image_name']
                    st.success("StreetView Agent completed successfully!")

                    # update entry table 
                    cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc1'] = 'Completed'
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc1_Bucket'] = streetview_bucket
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc1_Object'] = streetview_object
                    s3_write_csv(s3, st.session_state.df_entry_table, entry_bucket_name, entry_object_key)
                    
                    # display image
                    response = s3.get_object(Bucket=streetview_bucket, Key=streetview_object)
                    image_bytes = response['Body'].read()
                    st.image(image_bytes)
                else:
                    st.info("StreetView Agent failed to run. Please try again later.")
        else:
            streetview_bucket = st.session_state.client_entry['Proc1_Bucket']
            streetview_object = st.session_state.client_entry['Proc1_Object']

            response = s3.get_object(Bucket=streetview_bucket, Key=streetview_object)
            image_bytes = response['Body'].read()

            st.info("This client has already been processed by the StreetView Agent.")
            st.image(image_bytes, width=400)    

    # Run Webscraping agent
    if st.button("Run Webscraping Agent"):
        if pd.isna(st.session_state.client_entry['Proc2']):
            with st.spinner("Running AI agents..."):
                payload = {
                        "CLNT_NBR" : st.session_state.df_clnt_info['CU Number'],
                        "CUSTOMER_NAME" : st.session_state.df_clnt_info['Name'],
                        "OCCUPATION" : st.session_state.df_clnt_info['Position'],
                        "COMPANY" : st.session_state.df_clnt_info['Employer'],
                        "LOCATION" : st.session_state.df_clnt_info['Employer Address']
                    }
                response = invoke_lambda_function("externaldataprocesscode", payload=payload)

                if response['statusCode'] == 200:
                    external_data_bucket = response['bucket']
                    external_data_object = response['object_key']

                    st.success("Webscraping Agent completed successfully!")

                    cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc2'] = 'Completed'
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc2_Bucket'] = external_data_bucket
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc2_Object'] = external_data_object
                    s3_write_csv(s3, st.session_state.df_entry_table, entry_bucket_name, entry_object_key)

                    response = s3.get_object(Bucket=external_data_bucket, Key=external_data_object)
                    json_bytes = response['Body'].read()
                    st.download_button(
                        label="Download Webscraping Data",
                        data=json_bytes,
                        file_name=external_data_object,
                        mime='application/json'
                    )

                else:
                    st.error("Webscraping Agent failed to run.")
        else:
            st.info("This client has already been processed by the External Data Agent.")

    if st.button("Run Transcribe Agent"):     
        if pd.isna(st.session_state.client_entry['Proc3']):
            uploaded_file = st.file_uploader("Choose a file to upload")
            if uploaded_file is not None:
                # Read file bytes
                file_bytes = uploaded_file.read()
                # Define S3 bucket and object key (filename)
                upload_bucket = "doc-input-external"
                upload_key = uploaded_file.name

                # Upload to S3
                response = s3.put_object(Bucket=upload_bucket, Key=upload_key, Body=file_bytes)
                if response == 200:
                    s3.copy_object(
                        Bucket='doc-output-external',
                    )

                st.success(f"File '{uploaded_file.name}' uploaded to S3 bucket '{upload_bucket}'.")

                cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
                st.session_state.df_entry_table.loc[cu_pointer, 'Proc3'] = 'Completed'
                st.session_state.df_entry_table.loc[cu_pointer, 'Proc3_Bucket'] = external_data_bucket
                st.session_state.df_entry_table.loc[cu_pointer, 'Proc3_Object'] = external_data_object
                s3_write_csv(s3, st.session_state.df_entry_table, entry_bucket_name, entry_object_key)



    

if __name__ == "__main__":
    main()