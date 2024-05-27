import pandas as pd
from geopy.distance import geodesic
from datetime import datetime, timedelta

# Load GPS traces
gps_data = pd.read_csv('gps_data.csv', parse_dates=['Timestamp'])

# Load transit points (e.g., metro stations, bus stops)
transit_points = pd.read_csv('transit_points.csv')  # Columns: Latitude, Longitude, Type

# Load transit routes (e.g., metro lines, bus routes)
transit_routes = pd.read_csv('transit_routes.csv')  # Columns: RouteID, Latitude, Longitude, Sequence

# Sort the GPS data by DeviceID and Timestamp
gps_data.sort_values(by=['DeviceID', 'Timestamp'], inplace=True)

# Sort the transit routes by RouteID and Sequence
transit_routes.sort_values(by=['RouteID', 'Sequence'], inplace=True)

DISTANCE_THRESHOLD = 100  # meters
TIME_THRESHOLD = 300  # seconds (5 minutes)

def identify_trips_dwells(gps_data):
    trips = []
    dwells = []
    
    for device_id, device_data in gps_data.groupby('DeviceID'):
        device_data = device_data.sort_values('Timestamp').reset_index(drop=True)
        
        start_dwell = None
        start_trip = None
        
        for i in range(1, len(device_data)):
            point1 = (device_data.loc[i-1, 'Latitude'], device_data.loc[i-1, 'Longitude'])
            point2 = (device_data.loc[i, 'Latitude'], device_data.loc[i, 'Longitude'])
            
            distance = geodesic(point1, point2).meters
            time_diff = (device_data.loc[i, 'Timestamp'] - device_data.loc[i-1, 'Timestamp']).total_seconds()
            
            if distance < DISTANCE_THRESHOLD:
                if time_diff > TIME_THRESHOLD:
                    if not start_dwell:
                        start_dwell = device_data.loc[i-1, 'Timestamp']
                    end_dwell = device_data.loc[i, 'Timestamp']
                if start_trip:
                    trips.append({
                        'DeviceID': device_id,
                        'Start': start_trip,
                        'End': device_data.loc[i-1, 'Timestamp']
                    })
                    start_trip = None
            else:
                if start_dwell:
                    dwells.append({
                        'DeviceID': device_id,
                        'Start': start_dwell,
                        'End': end_dwell
                    })
                    start_dwell = None
                if not start_trip:
                    start_trip = device_data.loc[i-1, 'Timestamp']
        
        if start_trip:
            trips.append({
                'DeviceID': device_id,
                'Start': start_trip,
                'End': device_data.loc[i-1, 'Timestamp']
            })
        if start_dwell:
            dwells.append({
                'DeviceID': device_id,
                'Start': start_dwell,
                'End': end_dwell
            })
    
    return pd.DataFrame(trips), pd.DataFrame(dwells)

# Run the function
trips_df, dwells_df = identify_trips_dwells(gps_data)

def identify_mode_of_transport(trips_df, transit_points, transit_routes):
    modes = []
    
    for _, trip in trips_df.iterrows():
        start_point = (trip['Start_Latitude'], trip['Start_Longitude'])
        end_point = (trip['End_Latitude'], trip['End_Longitude'])
        
        # Check proximity to transit points
        for _, point in transit_points.iterrows():
            transit_point = (point['Latitude'], point['Longitude'])
            if geodesic(start_point, transit_point).meters < DISTANCE_THRESHOLD or geodesic(end_point, transit_point).meters < DISTANCE_THRESHOLD:
                modes.append({
                    'DeviceID': trip['DeviceID'],
                    'Trip_Start': trip['Start'],
                    'Trip_End': trip['End'],
                    'Mode': point['Type']
                })
                break
        
        # Check proximity to transit routes
        for route_id in transit_routes['RouteID'].unique():
            route_data = transit_routes[transit_routes['RouteID'] == route_id]
            for i in range(1, len(route_data)):
                route_point1 = (route_data.iloc[i-1]['Latitude'], route_data.iloc[i-1]['Longitude'])
                route_point2 = (route_data.iloc[i]['Latitude'], route_data.iloc[i]['Longitude'])
                if (geodesic(start_point, route_point1).meters < DISTANCE_THRESHOLD or geodesic(start_point, route_point2).meters < DISTANCE_THRESHOLD or
                    geodesic(end_point, route_point1).meters < DISTANCE_THRESHOLD or geodesic(end_point, route_point2).meters < DISTANCE_THRESHOLD):
                    modes.append({
                        'DeviceID': trip['DeviceID'],
                        'Trip_Start': trip['Start'],
                        'Trip_End': trip['End'],
                        'Mode': 'Bus' if 'bus' in route_id.lower() else 'Metro'
                    })
                    break
    
    return pd.DataFrame(modes)

# Add latitude and longitude information to trips_df for start and end points
trips_df['Start_Latitude'] = gps_data.groupby('DeviceID').apply(lambda x: x.iloc[0]['Latitude'])
trips_df['Start_Longitude'] = gps_data.groupby('DeviceID').apply(lambda x: x.iloc[0]['Longitude'])
trips_df['End_Latitude'] = gps_data.groupby('DeviceID').apply(lambda x: x.iloc[-1]['Latitude'])
trips_df['End_Longitude'] = gps_data.groupby('DeviceID').apply(lambda x: x.iloc[-1]['Longitude'])

# Run the function
modes_df = identify_mode_of_transport(trips_df, transit_points, transit_routes)

# Save the results
modes_df.to_csv('modes_of_transport.csv', index=False)

# Display the first few rows of the results
print("Modes of Transport:")
print(modes_df.head())

