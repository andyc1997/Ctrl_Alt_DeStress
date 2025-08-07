'''
Environment Variables / Parameters:
    # ADD_SRC_S3_BUCKET : string, S3 bucket for database of customer data
    GM_API_KEY : string, Personal Google Geocoding API
    IMAGE_S3_BUCKET : string, S3 bucket for storing the street view image
    # SRC_FILE_NAME : string, S3 bucket for file name of customer data ADD_SRC_S3_BUCKET

Event Json Parameters:
    CLNT_NBR : string, a customer number
    ADDRRESS : string, customer's company address
    *sample json input : {
                            "CLNT_NBR" : "123456704",
                            "ADDRESS" : "270 Park Avenue,. New York City. ,. United States"
                         }

Returns:
    statusCode : integer, status code
    body : string, result statement
    address : address, customer address
    bucket : img_bucket_name, S3 bucket name for storing images
    image_name : .jpg, a street view image of customer's employer company address
'''

from geopy.geocoders import GoogleV3
import google_streetview.api
import boto3, csv, io, json, os

def lambda_handler(event, context):
    # Initialize the geolocator
    geolocator = GoogleV3(api_key=os.environ.get("GM_API_KEY"))

    # Initialize S3 client
    s3 = boto3.client('s3')

    # Initialize bucket name
    img_bucket_name = os.environ.get("IMAGE_S3_BUCKET")
    # add_src_bucket_name = os.environ.get("ADD_SRC_S3_BUCKET")
    # src_file = os.environ.get("SRC_FILE_NAME")

    # Get customer number from event json input
    cu = event['CLNT_NBR']
    address = str(event['ADDRESS']).strip()

    # Get address from real customer list by customer number
    # response = s3.get_object(Bucket=add_src_bucket_name, Key=src_file)
    # file_content = response['Body'].read().decode('utf-8')
    # csv_reader = csv.reader(io.StringIO(file_content))
    # for row in csv_reader:
        # print(row)
        # if row[0] == cu:
            # address = row[13]
            # cu_name = row[1]
            # company = row[4]
            # occupation = row[3]
            # break
    # print(address)
    # Perform the geocoding
    location = geolocator.geocode(address)
    
    # Extract and print the latitude and longitude
    # if location:
        # print(f"Address: {location.address}")
        # print(f"Latitude: {location.latitude}")
        # print(f"Longitude: {location.longitude}")
    if not location:
        print("Could not find coordinates for the given address.")
        return {
            'statusCode': 200,
            'body': json.dumps('Could not find coordinates for the given address.')
        }

    coordinate=','.join([str(location.latitude), str(location.longitude)])
    print(coordinate)
    # Define parameters for street view api
    params = [{
      'size': '640x640', # max 640x640 pixels
      'location': coordinate,
      'heading': '205',
      'pitch': '55',
      'key': os.environ.get("GM_API_KEY")
    }]
    
    # Create a results object
    results = google_streetview.api.results(params)
    # results.preview()

    # Download images to directory path
    results.download_links(f"/tmp/images/")

    for filename in os.listdir("/tmp/images"):
        s3.upload_file(f"/tmp/images/{filename}", img_bucket_name, filename)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Found Street View'),
        'address': address,
        'bucket': img_bucket_name,
        'image_name': "gsv_0.jpg",
        # 'cu_name': cu_name,
        # 'company': occupation,
        # 'industry'
    }
