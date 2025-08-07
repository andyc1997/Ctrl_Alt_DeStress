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
    s3 = boto3.client('s3')

    # Get entry details
    entry_bucket_name = 'client-master-entry'
    entry_object_key = 'clnt_master_entry.csv'

    # Initialize session state variables
    if 'client_entry' not in st.session_state:
        st.session_state.client_entry = None
    if 'df_clnt_info' not in st.session_state:
        st.session_state.df_clnt_info = None
    if 'df_all_clnt_info' not in st.session_state:
        st.session_state.df_all_clnt_info = None
    if 'run_streetview' not in st.session_state:
        st.session_state.run_streetview = False
    
    if st.button("Create New Case"):
        if client_id:
            is_new_case, client_entry = create_client_entry(str(client_id))  
            if is_new_case:
                st.success(f"New case for client '{client_id}' created successfully!")
            else:
                st.error(f"New case for client '{client_id}' already exists or could not be created.")
        else:
            st.error("Please enter a valid Client ID.")
        st.session_state.client_entry = client_entry.iloc[0].to_dict()
    
    # Check if client entry exists 
    if st.button("Check Client ID"):
        if client_id:
            is_new_case, client_entry = check_client_entry(str(client_id))
            if is_new_case:
                st.info(f"The client for '{client_id}' does not exist.")
            else:
                st.success(f"The client for '{client_id}' exists.")
                st.session_state.client_entry = client_entry.iloc[0].to_dict()
                st.dataframe(client_entry)
        else:
            st.info("Please enter a valid Client ID.")
    
    if st.button("Run Data Processing"):
        if client_id:
            with st.spinner("Running Data Processing..."):
                internal_data_bucket = "internaldataprocess"
                internal_data_object = "real_cu_list.csv"

                # Download CSV from S3
                response = s3.get_object(Bucket=internal_data_bucket, Key=internal_data_object)
                csv_content = response['Body'].read().decode('utf-8')
                df = pd.read_csv(StringIO(csv_content), skiprows=10)
                df_clnt_info = df[df['CU Number'].astype(str) == str(client_id)]
            st.session_state.df_all_clnt_info = df.copy()
            st.session_state.df_clnt_info = df_clnt_info.iloc[0].to_dict()
            st.dataframe(df_clnt_info)                
        else:
            st.info("This client ID does not exist. Please create a new case first.")
        
    if st.button("Run StreetView Agent"):
        if pd.isna(st.session_state.client_entry['Proc1']):
            with st.spinner("Running AI agents..."):
                payload = {'CLNT_NBR': st.session_state.df_clnt_info['CU Number'], 
                           'ADDRESS': st.session_state.df_clnt_info['Employer Address']}
                response = invoke_lambda_function("street_view", payload=payload)

                if response['statusCode'] == 200:
                    streetview_bucket = response['bucket']
                    streetview_object = response['image_name']

                    st.success("StreetView Agent completed successfully!")
                    cu_pointer = st.session_state.df_all_clnt_info['CU Number'].astype(str) == str(client_id)
                    st.session_state.df_all_clnt_info[cu_pointer]['Proc1'] = 'Completed'
                    st.session_state.df_all_clnt_info[cu_pointer]['Proc1_Bucket'] = streetview_bucket
                    st.session_state.df_all_clnt_info[cu_pointer]['Proc1_Object'] = streetview_object

                    csv_buffer = StringIO()
                    st.session_state.df_all_clnt_info.to_csv(csv_buffer, index=False)
                    s3.put_object(Bucket=entry_bucket_name, Key=entry_object_key, Body=csv_buffer.getvalue())
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
            st.image(image_bytes, width=400)

        st.info("This client has already been processed by the StreetView Agent.")

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
                response = invoke_lambda_function("amazon_titan_s", payload=payload)

                if response['statusCode'] == 200:
                    external_data_bucket = response['bucket']
                    external_data_object = response['object_key']

                    st.success("External Data Agent completed successfully!")
                    st.session_state.client_entry['Proc2'] = 'Completed'
                    st.session_state.client_entry['Proc2_Bucket'] = external_data_bucket
                    st.session_state.client_entry['Proc2_Object'] = external_data_object

                    st.success("Webscraping Agent completed successfully!")
                    st.write(response['url_statements'])
                else:
                    st.error("Webscraping Agent failed to run.")
        else:
            st.error("This client has already been processed by the External Data Agent.")
if __name__ == "__main__":
    main()