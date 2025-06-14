from flask import Flask, render_template, jsonify
import random
from datetime import datetime
import csv
import os
import time # Import time module for Unix timestamp

app = Flask(__name__)

# Initialize data storage
time_data = [] # Will store Unix timestamps in milliseconds
motor_temp_data = []
voltage_data = []
current_data = []
torque_data = []
throttle_data = []
g_force_x_data = []
g_force_y_data = []

# Global state for lap times and session start
session_start_time = time.time() # Unix timestamp (seconds) when app starts
last_lap_reset_time = time.time() # Unix timestamp (seconds) for current lap start
best_lap_time = float('inf') # Store in seconds

csv_file = "evr_data_log.csv"

# Initialize mock data
mock_data = {
    "voltage": 48.0, 
    "motor_temp": 60.0, 
    "throttle": 0,
    "torque": 0.0, 
    "current": 0.0, 
    "g_force_x": 0.0, 
    "g_force_y": 0.0,
    "soc": 100.0,
    "soc_prev": 100.0 # To track previous SoC for trend calculation
}

def generate_mock_data(prev_data):
    # Store prev_data["soc"] before modifying for accurate trend calculation
    prev_soc = prev_data["soc"] 

    voltage = prev_data["voltage"] + random.uniform(-0.5, 0.5)
    voltage = max(40.0, min(60.0, voltage))

    motor_temp = prev_data["motor_temp"] + random.uniform(-1.0, 2.0)
    motor_temp = max(50.0, min(100.0, motor_temp))

    throttle = prev_data["throttle"] + random.randint(-5, 5)
    throttle = max(0, min(100, throttle))

    torque = prev_data["torque"] + random.uniform(-2.0, 3.0)
    torque = max(0.0, min(60.0, torque))

    current = prev_data["current"] + random.uniform(-3.0, 4.0)
    current = max(0.0, min(90.0, current))

    g_force_x = prev_data["g_force_x"] + random.uniform(-0.1, 0.1)
    g_force_x = max(-2.0, min(2.0, g_force_x))

    g_force_y = prev_data["g_force_y"] + random.uniform(-0.1, 0.1)
    g_force_y = max(-2.0, min(2.0, g_force_y))

    soc = prev_data["soc"] - random.uniform(0.01, 0.05)
    soc = max(0.0, soc)

    return {
        "voltage": round(voltage, 2),
        "motor_temp": round(motor_temp, 1),
        "throttle": throttle,
        "torque": round(torque, 2),
        "current": round(current, 2),
        "g_force_x": round(g_force_x, 2),
        "g_force_y": round(g_force_y, 2),
        "soc": round(soc, 2),
        "soc_prev": prev_soc # Pass previous SoC for status/trend
    }

def compute_status_trend(key, value, prev_value=None): # prev_value is now optional for general use
    status = "normal"
    trend = "steady"

    if key == "soc":
        if value < 20: status = "critical"
        elif value < 40: status = "warning"
    elif key == "motor_temp":
        if value > 90: status = "critical"
        elif value > 75: status = "warning"
    elif key == "voltage":
        if value < 45 or value > 55: status = "critical"
        elif value < 47 or value > 53: status = "warning"
    elif key == "current":
        if value > 80: status = "critical"
        elif value > 60: status = "warning"
    elif key == "throttle":
        # No specific critical/warning for throttle itself, but can add if needed
        pass
    elif key == "torque":
        # No specific critical/warning for torque itself
        pass
    elif key == "g_force_x" or key == "g_force_y":
        if abs(value) > 1.5: status = "warning" # Consider critical for very high Gs

    if prev_value is not None:
        if value > prev_value:
            trend = "up"
        elif value < prev_value:
            trend = "down"
        else:
            trend = "steady"
    return status, trend

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    global mock_data, last_lap_reset_time, best_lap_time
    
    current_time_seconds = time.time() # Current Unix timestamp in seconds
    current_time_ms = int(current_time_seconds * 1000) # Current Unix timestamp in milliseconds

    # Generate new data
    mock_data = generate_mock_data(mock_data)
    
    # Calculate current lap time
    current_lap_duration = current_time_seconds - last_lap_reset_time

    # Simulate lap completion (e.g., every 60 seconds)
    lap_time_display = ""
    if current_lap_duration >= 60.0: # Simulate a lap every 60 seconds
        completed_lap_duration = current_lap_duration
        if completed_lap_duration < best_lap_time:
            best_lap_time = completed_lap_duration
        
        # Format completed lap time and best lap time
        lap_time_display = f"{int(completed_lap_duration // 60):02d}:{int(completed_lap_duration % 60):02d}:{int((completed_lap_duration * 1000) % 1000):03d}"
        if best_lap_time != float('inf'):
            best_lap_time_str = f"{int(best_lap_time // 60):02d}:{int(best_lap_time % 60):02d}:{int((best_lap_time * 1000) % 1000):03d}"
            lap_time_display += f" (Best: {best_lap_time_str})"
        
        last_lap_reset_time = current_time_seconds # Reset for new lap
        current_lap_duration = 0.0 # Reset current lap duration
    else:
        # Format current lap duration
        lap_time_display = f"{int(current_lap_duration // 60):02d}:{int(current_lap_duration % 60):02d}:{int((current_lap_duration * 1000) % 1000):03d}"
        if best_lap_time != float('inf'):
            best_lap_time_str = f"{int(best_lap_time // 60):02d}:{int(best_lap_time % 60):02d}:{int((best_lap_time * 1000) % 1000):03d}"
            lap_time_display += f" (Best: {best_lap_time_str})"
    
    # Store time series data (use current_time_ms for Frontend)
    time_data.append(current_time_ms)
    motor_temp_data.append(mock_data["motor_temp"])
    voltage_data.append(mock_data["voltage"])
    current_data.append(mock_data["current"])
    torque_data.append(mock_data["torque"])
    throttle_data.append(mock_data["throttle"])
    g_force_x_data.append(mock_data["g_force_x"])
    g_force_y_data.append(mock_data["g_force_y"])
    
    # Limit data points
    max_points = 200 # Match this with config.maxDataPoints in frontend
    if len(time_data) > max_points:
        time_data.pop(0)
        motor_temp_data.pop(0)
        voltage_data.pop(0)
        current_data.pop(0)
        torque_data.pop(0)
        throttle_data.pop(0)
        g_force_x_data.pop(0)
        g_force_y_data.pop(0)
    
    # Compute statuses and trends for KPIs
    kpi_statuses = {}
    kpi_statuses["soc"] = compute_status_trend("soc", mock_data["soc"], mock_data["soc_prev"])
    kpi_statuses["motor_temp"] = compute_status_trend("motor_temp", mock_data["motor_temp"]) # No prev_value for trend here
    kpi_statuses["voltage"] = compute_status_trend("voltage", mock_data["voltage"])
    kpi_statuses["current"] = compute_status_trend("current", mock_data["current"])
    kpi_statuses["throttle"] = compute_status_trend("throttle", mock_data["throttle"])
    kpi_statuses["torque"] = compute_status_trend("torque", mock_data["torque"])
    kpi_statuses["g_force_x"] = compute_status_trend("g_force_x", mock_data["g_force_x"])
    kpi_statuses["g_force_y"] = compute_status_trend("g_force_y", mock_data["g_force_y"])

    # CSV logging
    # Ensure header is only written once
    file_exists = os.path.exists(csv_file)
    with open(csv_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "Timestamp", "Lap Time", "SoC", "Motor Temp", "Voltage", "Current",
                "Throttle", "Torque", "G-Force X", "G-Force Y",
                "Motor Temp Status", "Voltage Status", "Current Status",
                "Throttle Status", "Torque Status", "G-Force X Status", "G-Force Y Status"
            ])
        
        writer.writerow([
            datetime.fromtimestamp(current_time_seconds).strftime('%Y-%m-%d %H:%M:%S'), # Use datetime object for CSV
            lap_time_display, mock_data["soc"], mock_data["motor_temp"],
            mock_data["voltage"], mock_data["current"], mock_data["throttle"], mock_data["torque"],
            mock_data["g_force_x"], mock_data["g_force_y"],
            kpi_statuses.get("motor_temp", {})[0],
            kpi_statuses.get("voltage", {})[0],
            kpi_statuses.get("current", {})[0],
            kpi_statuses.get("throttle", {})[0],
            kpi_statuses.get("torque", {})[0],
            kpi_statuses.get("g_force_x", {})[0],
            kpi_statuses.get("g_force_y", {})[0]
        ])
    
    # Prepare response
    response = {
        "kpis": {
            "Lap Time": {"value": lap_time_display, "status": "normal", "trend": "steady"},
            "SoC": {"value": mock_data["soc"], "unit": "%", "status": kpi_statuses["soc"][0], "trend": kpi_statuses["soc"][1]},
            "Motor Temp": {"value": mock_data["motor_temp"], "unit": "°C", "status": kpi_statuses["motor_temp"][0], "trend": kpi_statuses["motor_temp"][1]},
            "Voltage": {"value": mock_data["voltage"], "unit": "V", "status": kpi_statuses["voltage"][0], "trend": kpi_statuses["voltage"][1]},
            "Current": {"value": mock_data["current"], "unit": "A", "status": kpi_statuses["current"][0], "trend": kpi_statuses["current"][1]},
            "Throttle": {"value": mock_data["throttle"], "unit": "%", "status": kpi_statuses["throttle"][0], "trend": kpi_statuses["throttle"][1]},
            "Torque": {"value": mock_data["torque"], "unit": "Nm", "status": kpi_statuses["torque"][0], "trend": kpi_statuses["torque"][1]},
            "G-Force X": {"value": mock_data["g_force_x"], "unit": "g", "status": kpi_statuses["g_force_x"][0], "trend": kpi_statuses["g_force_x"][1]},
            "G-Force Y": {"value": mock_data["g_force_y"], "unit": "g", "status": kpi_statuses["g_force_y"][0], "trend": kpi_statuses["g_force_y"][1]},
        },
        "graphs": {
            "time_data": time_data, # Send full cached data
            "motor_temp_data": motor_temp_data,
            "voltage_data": voltage_data,
            "current_data": current_data,
            "g_force_x_data": g_force_x_data,
            "g_force_y_data": g_force_y_data,
            "throttle_data": throttle_data,
            "torque_data": torque_data,
        }
    }
    
    return jsonify(response)

if __name__ == '__main__':
    # Clear CSV file on startup for fresh logs
    if os.path.exists(csv_file):
        os.remove(csv_file)
    app.run(debug=True)
