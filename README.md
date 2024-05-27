# Mode of Transport Identification from GPS Data

This project identifies trips and their respective modes of transport from a large dataset of mobile phone GPS traces. The project uses data on GPS traces, key transit points (e.g., metro stations, bus stops), and trajectories of transit routes to determine whether each trip was taken by bus, metro, or another mode.

## Prerequisites

- Python 3.x
- Required Libraries: pandas, geopy

To install the required libraries, run:
```bash
pip install pandas geopy
```

## Dataset Files

1. **gps_data.csv**: Contains GPS traces with columns:
   - `DeviceID`: Identifier for the device
   - `Latitude`: Latitude coordinate
   - `Longitude`: Longitude coordinate
   - `Timestamp`: Timestamp of the GPS record

2. **transit_points.csv**: Contains transit points (e.g., metro stations, bus stops) with columns:
   - `Latitude`: Latitude coordinate
   - `Longitude`: Longitude coordinate
   - `Type`: Type of transit point (e.g., 'Metro', 'Bus Stop')

3. **transit_routes.csv**: Contains transit routes with columns:
   - `RouteID`: Identifier for the route
   - `Latitude`: Latitude coordinate
   - `Longitude`: Longitude coordinate
   - `Sequence`: Sequence number for the points in the route

## Code Explanation

### Step 1: Import Libraries

The necessary libraries are imported for data manipulation and geospatial calculations.

```python
import pandas as pd
from geopy.distance import geodesic
from datetime import datetime, timedelta
```

### Step 2: Load Data

Load the data from CSV files into pandas DataFrames.

```python
# Load GPS traces
gps_data = pd.read_csv('gps_data.csv', parse_dates=['Timestamp'])

# Load transit points (e.g., metro stations, bus stops)
transit_points = pd.read_csv('transit_points.csv')  # Columns: Latitude, Longitude, Type

# Load transit routes (e.g., metro lines, bus routes)
transit_routes = pd.read_csv('transit_routes.csv')  # Columns: RouteID, Latitude, Longitude, Sequence
```

### Step 3: Preprocess Data

Sort the GPS data by `DeviceID` and `Timestamp` to ensure chronological order, and sort the transit routes by `RouteID` and `Sequence` to ensure the correct order of route points.

```python
# Sort the GPS data by DeviceID and Timestamp
gps_data.sort_values(by=['DeviceID', 'Timestamp'], inplace=True)

# Sort the transit routes by RouteID and Sequence
transit_routes.sort_values(by=['RouteID', 'Sequence'], inplace=True)
```

### Step 4: Identify Trips and Dwells

Define a function to identify trips and dwells based on distance and time thresholds. A trip is considered when there is movement beyond a specified distance threshold, and a dwell is considered when there is little movement for a specified time threshold.

```python
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
                        'End': device_data.loc[i-1, 'Timestamp'],
                        'Start_Latitude': device_data.loc[i-1, 'Latitude'],
                        'Start_Longitude': device_data.loc[i-1, 'Longitude'],
                        'End_Latitude': device_data.loc[i, 'Latitude'],
                        'End_Longitude': device_data.loc[i, 'Longitude']
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
                'End': device_data.loc[i-1, 'Timestamp'],
                'Start_Latitude': device_data.loc[i-1, 'Latitude'],
                'Start_Longitude': device_data.loc[i-1, 'Longitude'],
                'End_Latitude': device_data.loc[i, 'Latitude'],
                'End_Longitude': device_data.loc[i, 'Longitude']
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
```

### Step 5: Identify Mode of Transport

Define a function to classify the mode of transport for each trip based on proximity to transit points and routes.

```python
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

# Run the function
modes_df = identify_mode_of_transport(trips_df, transit_points, transit_routes)

# Save the results
modes_df.to_csv('modes_of_transport.csv', index=False)

# Display the first few rows of the results
print("Modes of Transport:")
print(modes_df.head())
```

## Conclusion

This project provides a comprehensive method to identify trips and classify the mode of transport from GPS data. By leveraging proximity analysis to transit points and routes, it accurately determines whether each trip was taken by bus, metro, or another mode of transport. The results are saved in a CSV file for further analysis.
