"""
Sensor data simulation module for AgriGenius
Provides simulated agricultural sensor data
"""

import random
import time
from datetime import datetime


def get_sensor_data():
    """
    Simulate agricultural sensor data
    Returns a dictionary with various sensor readings
    """
    try:
        # Simulate realistic agricultural sensor data
        sensor_data = {
            'timestamp': datetime.now().isoformat(),
            'temperature': round(random.uniform(15.0, 35.0), 1),  # Celsius
            'humidity': round(random.uniform(30.0, 90.0), 1),     # Percentage
            'soil_moisture': round(random.uniform(20.0, 80.0), 1), # Percentage
            'ph_level': round(random.uniform(5.5, 8.0), 1),       # pH scale
            'light_intensity': round(random.uniform(200, 2000), 0), # Lux
            'nitrogen': round(random.uniform(10, 50), 1),         # ppm
            'phosphorus': round(random.uniform(5, 25), 1),        # ppm
            'potassium': round(random.uniform(15, 60), 1),        # ppm
            'status': 'active'
        }

        return sensor_data

    except Exception as e:
        # Return error data if something goes wrong
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'status': 'error'
        }


def get_sensor_recommendations(sensor_data):
    """
    Provide basic recommendations based on sensor data
    """
    recommendations = []

    try:
        if 'error' in sensor_data:
            return ['Sensor error detected. Please check sensor connections.']

        # Temperature recommendations
        if sensor_data.get('temperature', 0) > 30:
            recommendations.append('Temperature is high. Consider providing shade or increasing ventilation.')
        elif sensor_data.get('temperature', 0) < 18:
            recommendations.append('Temperature is low. Consider using greenhouse or heating.')

        # Humidity recommendations
        if sensor_data.get('humidity', 0) > 80:
            recommendations.append('Humidity is high. Improve air circulation to prevent fungal diseases.')
        elif sensor_data.get('humidity', 0) < 40:
            recommendations.append('Humidity is low. Consider misting or irrigation.')

        # Soil moisture recommendations
        if sensor_data.get('soil_moisture', 0) < 30:
            recommendations.append('Soil moisture is low. Watering is recommended.')
        elif sensor_data.get('soil_moisture', 0) > 70:
            recommendations.append('Soil moisture is high. Check drainage to prevent root rot.')

        # pH recommendations
        ph = sensor_data.get('ph_level', 7)
        if ph < 6.0:
            recommendations.append('Soil is acidic. Consider adding lime to raise pH.')
        elif ph > 7.5:
            recommendations.append('Soil is alkaline. Consider adding sulfur to lower pH.')

        # Nutrient recommendations
        if sensor_data.get('nitrogen', 0) < 20:
            recommendations.append('Nitrogen levels are low. Consider nitrogen-rich fertilizer.')
        if sensor_data.get('phosphorus', 0) < 10:
            recommendations.append('Phosphorus levels are low. Consider phosphorus fertilizer.')
        if sensor_data.get('potassium', 0) < 25:
            recommendations.append('Potassium levels are low. Consider potassium fertilizer.')

        if not recommendations:
            recommendations.append('All sensor readings are within optimal ranges!')

        return recommendations

    except Exception as e:
        return [f'Error generating recommendations: {str(e)}']