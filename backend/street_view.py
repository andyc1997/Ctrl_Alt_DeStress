'''
Parameters:
    address : string, customer address
    GM_API_KEY : string, Google Geocoding API
    path : string, directory for storing the street view image
'''

import google_streetview.api
from geopy.geocoders import GoogleV3

def street_view(address, GM_API_KEY, path):    
    # Initialize the geolocator
    geolocator = GoogleV3(api_key=GM_API_KEY)
    
    # Define the address
    # address = "1600 Amphitheatre Parkway, Mountain View, CA"
    
    # Perform the geocoding
    location = geolocator.geocode(address)
    
    # Extract and print the latitude and longitude
    if location:
        print(f"Address: {location.address}")
        print(f"Latitude: {location.latitude}")
        print(f"Longitude: {location.longitude}")
    else:
        print("Could not find coordinates for the given address.")

    coordinate=','.join([str(location.latitude), str(location.longitude)])
  
    # Define parameters for street view api
    params = [{
      'size': '600x300', # max 640x640 pixels
      'location': coordinate,
      'heading': '151.78',
      'pitch': '-0.76',
      'key': GM_API_KEY
    }]
    
    # Create a results object
    results = google_streetview.api.results(params)
    results.preview()

    # Download images to directory path
    results.download_links(path)
