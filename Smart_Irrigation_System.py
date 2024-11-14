import streamlit as st
import pandas as pd
import altair as alt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import os
import gspread
import datetime
import base64
import requests
import plotly.graph_objects as go
import time
from oauth2client.service_account import ServiceAccountCredentials


# Function to read the soil moisture level from Arduino
def read_soil_moisture():
    # The IP address of your ESP32 device
    esp32_ip = "http://192.168.101.147"  # Replace with your actual IP

    try:
        response = requests.get(esp32_ip)
        if response.status_code == 200:
            data = response.json()  # Get the JSON response
            soil_moisture = data['soil_moisture']
            return soil_moisture
        else:
            return None
    except Exception as e:
        return None

# Helper function to load user data
def load_users():
    if os.path.exists('users.csv'):
        return pd.read_csv('users.csv')
    else:
        return pd.DataFrame(columns=['Username', 'Password', 'Role'])

# Helper function to save user data
def save_user(username, password, role):
    users = load_users()
    new_user = pd.DataFrame([[username, password, role]], columns=['Username', 'Password', 'Role'])
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv('users.csv', index=False)

# Authentication and welcome page
def welcome_page():
    if not st.session_state.get('show_animation', False):
        st.balloons()  # Display animation only once
        st.session_state.show_animation = True  # Prevent showing again
    st.success("Login successful!")

# Function to encode image to base64 (for sidebar background)
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


# Function to apply light theme styles
def apply_light_theme():
    # Light theme styles
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f5f5f5;
            color: black;
        }
        .stSidebar {
            background-color: #ffffff;
            color: black;
        }
        </style>
        """, unsafe_allow_html=True)

# Main application logic
def main():
    # Set the page configuration
    st.set_page_config(page_title="SMART IRRI", page_icon=":shamrock:", layout="wide")

    apply_light_theme()  # Apply the light theme

    # Encode the background image to base64
    encoded_image = encode_image("background.png")  # Path to your background image
    encoded_imageSide = encode_image("backgroundSide.png")  # Path to your background image
    

   # Set custom CSS for the main background image
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url('data:image/png;base64,{encoded_image}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* Apply background to the sidebar */
        .css-1d391kg {{
            background-image: url('data:image/png;base64,{encoded_imageSide}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* Alternatively, we can target a broader CSS class for the sidebar */
        .stSidebar {{
            background-image: url('data:image/png;base64,{encoded_imageSide}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """, unsafe_allow_html=True
    )
    
    # Initialize session state for login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.show_animation = False
        
    # Display logo before login
    st.image("logo.png", use_column_width=True)  # Path to your logo file
    # Centering the title using HTML and Markdown
    st.markdown("<h1 style='text-align: center;'>Welcome to SMART IRRI</h1>", unsafe_allow_html=True)

    # Authentication
    st.sidebar.title("Login or Register")
    auth_type = st.sidebar.selectbox("Select", ["Login", "Register"])
    auth_user = st.sidebar.text_input("Username")
    auth_pass = st.sidebar.text_input("Password", type="password")
    role = None

   
    if auth_type == "Register":
        role = st.sidebar.selectbox("Register as", ["Farmer/Client", "Maintenance Worker"])
        if st.sidebar.button("Register"):
            save_user(auth_user, auth_pass, role)
            st.sidebar.success(f"User {auth_user} registered successfully!")

    users = load_users()

    # Login functionality
    user_data = users[(users['Username'] == auth_user) & (users['Password'] == auth_pass)]
    if not user_data.empty:
        role = user_data.iloc[0]['Role']
        st.sidebar.success(f"Welcome, {auth_user}! Role: {role}")
        st.session_state.logged_in = True  # Set the login state to True

        # Display welcome page
        welcome_page()

        # Main functionality selection
        functionality = st.selectbox("Select Functionality", ["Real-Time Control", "Sensor Data Analysis"])

        if functionality == "Sensor Data Analysis":
            sensor_analysis()
        elif functionality == "Real-Time Control":
            real_time_control()
    else:
        if auth_user or auth_pass:
            st.sidebar.error("Invalid username or password!")

def generate_pdf_report(sensor_data, avg_soil_moisture, suggestions, charts, avg_temp, avg_humidity, user_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Cover Page
    p.setFont("Helvetica-Bold", 24)
    # Add Logo
    logo_path = "logo.png"  # Path to your logo image
    p.drawImage(logo_path, width / 2 - 200, height - 300, width=400, height=200)  # Adjust position and size as needed
    p.drawCentredString(width / 2, height - 360, "Soil Moisture Analysis Report")

    # User Details
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, height - 400, f"Prepared for: {user_name}")
    p.drawCentredString(width / 2, height - 430, f"Date Generated: {datetime.datetime.now().strftime('%Y-%m-%d')}")

    # Page Break
    p.showPage()

    # Data Summary Section
    p.setFont("Helvetica", 12)
    p.drawString(72, height - 72, "Summary of Sensor Data:")

    # Write sensor data (Display Date, Soil Moisture Level, Temperature, Humidity)
    y_position = height - 100
    for i, row in sensor_data.iterrows():
        if y_position < 72:  # If the position is too low, start a new page
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 72

        p.drawString(72, y_position, f"Date: {row['Datetime']}, Soil Moisture Level: {row['Soil_Moisture_Level']}%, "
                                     f"Temperature: {row['Temperature']}°C, Humidity: {row['Humidity']}%")
        y_position -= 20  # Move down for the next entry

    # Page Break for Average Values
    p.showPage()
    p.setFont("Helvetica", 12)
    p.drawString(72, height - 72, f"Average Soil Moisture Level: {avg_soil_moisture:.2f}%")
    p.drawString(72, height - 92, f"Average Temperature: {avg_temp:.2f}°C")
    p.drawString(72, height - 112, f"Average Humidity: {avg_humidity:.2f}%")

    # Recommendations based on soil moisture levels
    p.drawString(72, height - 152, "Recommendations:")
    y_position = height - 172
    for suggestion in suggestions:
        if y_position < 72:  # Start a new page if necessary
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 72

        p.drawString(72, y_position, f"- {suggestion}")
        y_position -= 20

    # Save and Add charts to PDF
    for i, chart in enumerate(charts):
        # Save each chart as a PNG image
        chart_img_path = f"chart_{i}.png"
        chart.save(chart_img_path, format='png')  # Save the chart to a file

        # Add the chart image to the PDF
        p.showPage()  # Start a new page for each chart
        p.drawImage(chart_img_path, 72, height - 400, width=500, height=300)  # Adjust coordinates and size as needed

    p.showPage()  # Finalize the PDF
    p.save()
    buffer.seek(0)

    return buffer




# Sensor Data Analysis functionality
def sensor_analysis():
    st.header("Sensor Data Analysis")
    
    # Instructions for the user
    st.markdown("""
    **Instructions:**
    1. Please upload a CSV file containing your sensor data.
    2. The CSV file should have the following columns:
       - `Datetime`: The combined date and time of the reading.
       - `Soil_Moisture_Level`: The measured soil moisture level (in percentage).
       - `Temperature`: The temperature at the time of reading (in Celsius).
       - `Humidity`: The humidity at the time of reading (in percentage).
    3. Once the file is uploaded, the system will analyze the data and provide insights and recommendations.
    4. After reviewing the analysis, you can generate a report by clicking the button below.
    """)
    
    uploaded_file = st.file_uploader("Upload Sensor Data (CSV)", type="csv")

    # Inside sensor_analysis function
    if uploaded_file:
        # Read the CSV file
        sensor_data = pd.read_csv(uploaded_file)

        # Convert the Datetime column to datetime format
        sensor_data['Datetime'] = pd.to_datetime(sensor_data['Datetime'])

        # Display the uploaded data
        st.write(sensor_data)

        # Visualizations
        soil_moisture_chart = alt.Chart(sensor_data).mark_line().encode(
            x='Datetime:T',
            y='Soil_Moisture_Level:Q'
        ).properties(title="Soil Moisture Level Monitoring Over Time")

        temperature_chart = alt.Chart(sensor_data).mark_line(color='red').encode(
            x='Datetime:T',
            y='Temperature:Q'
        ).properties(title="Temperature Monitoring Over Time")

        humidity_chart = alt.Chart(sensor_data).mark_line(color='blue').encode(
            x='Datetime:T',
            y='Humidity:Q'
        ).properties(title="Humidity Monitoring Over Time")

        moisture_histogram = alt.Chart(sensor_data).mark_bar().encode(
            alt.X('Soil_Moisture_Level:Q', bin=True),
            y='count()'
        ).properties(title="Distribution of Soil Moisture Levels")


        # Average calculations
        avg_temp = sensor_data['Temperature'].mean()
        avg_humidity = sensor_data['Humidity'].mean()

        # Suggestions
        avg_soil_moisture = sensor_data['Soil_Moisture_Level'].mean()
        suggestions = []
        if avg_soil_moisture < 21:
            suggestions.append("Very low soil moisture! Immediate irrigation is recommended.")
        elif avg_soil_moisture < 41:
            suggestions.append("Low soil moisture. Consider increasing irrigation frequency.")
        elif avg_soil_moisture < 71:
            suggestions.append("Optimal soil moisture levels. Continue current irrigation practices.")
        else:
            suggestions.append("High soil moisture. Reduce irrigation to avoid overwatering.")

        total_performance_chart = alt.Chart(sensor_data).transform_fold(
            ['Soil_Moisture_Level', 'Temperature', 'Humidity'],  # Columns to fold (combine)
            as_=['Metric', 'Value']  # Metric will be used to distinguish between soil moisture, temperature, and humidity
        ).mark_line().encode(
            x='Datetime:T',  # Datetime as X-axis
            y='Value:Q',  # Values of metrics (soil moisture, temperature, humidity) on the Y-axis
            color='Metric:N'  # Different color for each metric
        ).properties(
            title="Total Performance of Soil Moisture, Temperature, and Humidity Over Time"
        )

        # Display charts
        st.altair_chart(soil_moisture_chart, use_container_width=True)
        st.altair_chart(temperature_chart, use_container_width=True)
        st.altair_chart(humidity_chart, use_container_width=True)
        st.altair_chart(moisture_histogram, use_container_width=True)
        st.altair_chart(total_performance_chart, use_container_width=True)

        # Display average temperature and humidity
        st.write(f"Average Temperature: {avg_temp:.2f}°C")
        st.write(f"Average Humidity: {avg_humidity:.2f}%")

        # Button to generate report
        user_name = "Farmer John"  # Replace with user input if necessary
        if st.button("Generate Report"):
            # Include all charts
            charts = [
                soil_moisture_chart,
                temperature_chart,
                humidity_chart,
                moisture_histogram,
                total_performance_chart  # Add Total Performance chart
            ]
            pdf_buffer = generate_pdf_report(sensor_data, avg_soil_moisture, suggestions, charts, avg_temp, avg_humidity, user_name=user_name)
            st.download_button("Download PDF Report", pdf_buffer, "sensor_data_report.pdf", "application/pdf")



# Add session state variables for the auto-control
if 'water_pump_status' not in st.session_state:
    st.session_state.water_pump_status = "OFF"  # Initial status of the water pump
if 'water_pump_status_displayed' not in st.session_state:
    st.session_state.water_pump_status_displayed = False  # Track if the status display was already created

# Real-Time Control functionality
def real_time_control():
    st.header("Soil Moisture Monitoring")

    # Initialize the placeholders for real-time updates
    soil_moisture_display = st.empty()
    soil_moisture_value_display = st.empty()
    soil_moisture_chart_display = st.empty()

    while True:
        # Get the real-time soil moisture level from Arduino
        soil_moisture_level = read_soil_moisture()

        if soil_moisture_level is not None:
            # Display the current soil moisture level using a slider (disabled for display purposes)
            key = f"soil_moisture_slider_{soil_moisture_level}_{int(time.time())}"
            soil_moisture_display.slider("Current Soil Moisture Level", 0, 100, soil_moisture_level, key=key, disabled=True)

            # Create centered layout
            col1, col2, col3 = st.columns([1, 3, 1])  # Adjust column widths to center content

            with col2:  # Center the content in the middle column
                if not hasattr(st.session_state, 'label_displayed'):  # Display label once
                    st.markdown("<h3 style='text-align: center;'>Soil Moisture Level</h3>", unsafe_allow_html=True)
                    st.session_state.label_displayed = True

                # Dynamically update the value display
                soil_moisture_value_display.empty()  # Clear previous value
                soil_moisture_value_display.markdown(f"<h1 style='text-align: center; font-size: 60px;'>{soil_moisture_level}%</h1>", unsafe_allow_html=True)

            # Create the car-meter style gauge chart
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=soil_moisture_level,
                title={'text': "Soil Moisture Level"},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': "lightblue"},
                       'steps': [
                           {'range': [0, 20], 'color': "red"},
                           {'range': [20, 50], 'color': "yellow"},
                           {'range': [50, 100], 'color': "green"}],
                       'threshold': {'line': {'color': "blue", 'width': 4}, 'thickness': 0.75, 'value': soil_moisture_level}}))

            # Update the chart dynamically using the placeholder
            chart_key = f"soil_moisture_chart_{int(time.time())}"
            soil_moisture_chart_display.plotly_chart(fig, use_container_width=True, key=chart_key)

            # Water Pump Control - Auto mode logic
            if soil_moisture_level < 50:
                # Automatically turn the water pump ON if moisture is below 50%
                st.session_state.water_pump_status = "ON"
            else:
                # Automatically turn the water pump OFF if moisture is 50% or higher
                st.session_state.water_pump_status = "OFF"

            # Water Pump Status Display Section - Display it once, then only update status dynamically
            if not st.session_state.water_pump_status_displayed:
                st.session_state.water_pump_status_displayed = True  # Track that we've displayed the status section once

                # Placeholder for the status display
                st.session_state.water_pump_status_placeholder = st.empty()

            # Dynamically update the status display only when water pump status changes
            pump_emoji = "💧" if st.session_state.water_pump_status == "ON" else "🚫💧"
            pump_status_color = "green" if st.session_state.water_pump_status == "ON" else "red"

            # Update the water pump status display dynamically in the placeholder
            st.session_state.water_pump_status_placeholder.markdown(
                f"<h3 style='text-align:center; color:{pump_status_color}; font-size: 30px;'>{pump_emoji} Water Pump Status</h3>"
                f"<h1 style='text-align: center; font-size: 80px;'>{st.session_state.water_pump_status}</h1>",
                unsafe_allow_html=True
            )

        else:
            # Display an error message if data could not be fetched
            soil_moisture_display.error("Failed to read data from the sensor.")

        # Refresh the page every 1 second to simulate real-time data fetching
        time.sleep(1)

    
# Run the application
if __name__ == "__main__":
    main()
