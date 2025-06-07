import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Radius of Earth in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

def calculate_fare(distance_km, vehicle_type='SEDAN', base_fare=50, rate_per_km=15, surge_multiplier=1.0):
    """
    Calculate the estimated fare for a ride.
    
    Parameters:
    - distance_km (float): The distance of the ride in kilometers.
    - vehicle_type (str): The type of vehicle (e.g., 'SEDAN', 'SUV'). Affects rate or base.
    - base_fare (float): The minimum charge for a ride.
    - rate_per_km (float): The charge per kilometer.
    - surge_multiplier (float): A multiplier for dynamic pricing during peak hours.
    
    Returns:
    - float: The estimated fare.
    """
    # Vehicle-specific adjustments (example)
    if vehicle_type == 'SUV':
        rate_per_km *= 1.2 # SUVs might be 20% more expensive per km
        base_fare *= 1.1   # And have a slightly higher base fare
    elif vehicle_type == 'HATCHBACK':
        rate_per_km *= 0.9 # Hatchbacks might be 10% cheaper

    estimated_fare = (base_fare + (distance_km * rate_per_km)) * surge_multiplier
    
    # Ensure fare is not below a minimum threshold (e.g., base_fare itself after surge)
    min_total_fare = base_fare * surge_multiplier
    return max(estimated_fare, min_total_fare)

def predict_eta(distance_km, average_speed_kmh=30):
    """
    Predict the Estimated Time of Arrival (ETA) for a ride.
    
    Parameters:
    - distance_km (float): The distance of the ride in kilometers.
    - average_speed_kmh (float): The assumed average speed in kilometers per hour.
    
    Returns:
    - float: The estimated time in minutes.
    """
    if average_speed_kmh <= 0:
        return float('inf') # Or handle as an error
        
    time_hours = distance_km / average_speed_kmh
    time_minutes = time_hours * 60
    return time_minutes

# Example usage (can be removed or kept for testing):
if __name__ == '__main__':
    # Test distance calculation (e.g., two points in a city)
    lat1, lon1 = 12.9716, 77.5946 # Bangalore
    lat2, lon2 = 13.0827, 80.2707 # Chennai
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    print(f"Distance: {distance:.2f} km")

    # Test fare calculation
    fare_sedan = calculate_fare(distance_km=10, vehicle_type='SEDAN')
    fare_suv_surge = calculate_fare(distance_km=15, vehicle_type='SUV', surge_multiplier=1.5)
    print(f"Fare (Sedan, 10km): INR {fare_sedan:.2f}")
    print(f"Fare (SUV, 15km, Surge 1.5x): INR {fare_suv_surge:.2f}")

    # Test ETA prediction
    eta = predict_eta(distance_km=10, average_speed_kmh=25)
    print(f"ETA (10km at 25km/h): {eta:.2f} minutes")
