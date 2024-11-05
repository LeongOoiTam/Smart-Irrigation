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
from oauth2client.service_account import ServiceAccountCredentials

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
    st.title("Welcome to SMART IRRI")
    if not st.session_state.get('show_animation', False):
        st.balloons()  # Display animation only once
        st.session_state.show_animation = True  # Prevent showing again
    st.success("Login successful!")

# Main application logic
def main():
    # Initialize session state for login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.show_animation = False

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
        functionality = st.selectbox("Select Functionality", ["Sensor Data Analysis", "Real-Time Control"])

        if functionality == "Sensor Data Analysis":
            sensor_analysis()
        elif functionality == "Real-Time Control":
            real_time_control()
    else:
        if auth_user or auth_pass:
            st.sidebar.error("Invalid username or password!")


def generate_pdf_report(sensor_data, avg_soil_moisture, suggestions, charts, user_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Cover Page
    p.setFont("Helvetica-Bold", 24)
     # Add Logo
    logo_path = "logo.png"  # Path to your logo image
    p.drawImage(logo_path, width / 2 - 200 , height - 300, width=400, height=200)  # Adjust position and size as needed
    p.drawCentredString(width / 2, height - 360, "Soil Moisture Analysis Report")

    # User Details
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, height - 400, f"Prepared for: {user_name}")
    p.drawCentredString(width / 2, height - 430, f"Date Generated: {datetime.datetime.now().strftime('%Y-%m-%d')}")

    # Page Break
    p.showPage()

    # Data Summary Section
    p.setFont("Helvetica", 12)
    p.drawString(72, height - 72, "Summary of Soil Moisture Data:")
    
    # Write sensor data
    y_position = height - 100
    for i, row in sensor_data.iterrows():
        if y_position < 72:  # If the position is too low, start a new page
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 72
        
        p.drawString(72, y_position, f"Date: {row['Date']}, Soil Moisture Level: {row['Soil_Moisture_Level']}%")
        y_position -= 20  # Move down for the next entry

    # Average Soil Moisture
    p.showPage()
    p.setFont("Helvetica", 12)
    p.drawString(72, height - 72, f"Average Soil Moisture Level: {avg_soil_moisture:.2f}%")

    # Recommendations
    p.drawString(72, height - 92, "Recommendations:")
    for i, suggestion in enumerate(suggestions):
        y_position = height - 112 - (i * 20)
        if y_position < 72:  # Start a new page if necessary
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 72
        
        p.drawString(72, y_position, f"- {suggestion}")

    # Add charts to PDF
    for chart_img in charts:
        p.showPage()  # Start a new page for each chart
        p.drawImage(chart_img, 72, height - 400, width=500, height=300)  # Adjust coordinates and size as needed

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
    1. Please upload a CSV file containing your soil moisture sensor data.
    2. The CSV file should have the following columns:
       - `Date`: Date of the reading.
       - `Soil_Moisture_Level`: The measured soil moisture level (in percentage).
       - `Sensor`: Identifier for the sensor (optional if multiple sensors are used).
    3. Once the file is uploaded, the system will analyze the data and provide insights and recommendations.
    4. After reviewing the analysis, you can generate a report by clicking the button below.
    """)
    
    uploaded_file = st.file_uploader("Upload Sensor Data (CSV)", type="csv")

    if uploaded_file:
        sensor_data = pd.read_csv(uploaded_file)
        st.write(sensor_data)

        # Visualization: Soil Moisture Levels
        soil_moisture_chart = alt.Chart(sensor_data).mark_line().encode(
            x='Date:T',
            y='Soil_Moisture_Level:Q',
            color='Sensor:N'
        ).properties(title="Soil Moisture Level Monitoring")

        # Save the chart as an image
        soil_moisture_chart_image = f"soil_moisture_chart.png"
        soil_moisture_chart.save(soil_moisture_chart_image)

        st.altair_chart(soil_moisture_chart, use_container_width=True)

        # Histogram of Soil Moisture Levels
        histogram = alt.Chart(sensor_data).mark_bar().encode(
            alt.X('Soil_Moisture_Level:Q', bin=True),
            y='count()',
            color='Sensor:N'
        ).properties(title="Distribution of Soil Moisture Levels")
        
        # Save histogram as an image
        histogram_image = f"histogram.png"
        histogram.save(histogram_image)

        st.altair_chart(histogram, use_container_width=True)

        # Moving Average
        sensor_data['Moving_Average'] = sensor_data['Soil_Moisture_Level'].rolling(window=3).mean()
        moving_average_chart = alt.Chart(sensor_data).mark_line(color='orange').encode(
            x='Date:T',
            y='Moving_Average:Q'
        ).properties(title="Moving Average of Soil Moisture Levels")
        
        # Save moving average chart as an image
        moving_average_chart_image = f"moving_average_chart.png"
        moving_average_chart.save(moving_average_chart_image)

        st.altair_chart(moving_average_chart, use_container_width=True)

        # Suggestions based on data
        avg_soil_moisture = sensor_data['Soil_Moisture_Level'].mean()
        suggestions = []  # Initialize suggestions list
        if avg_soil_moisture < 21:
            suggestions.append("Very low soil moisture! Immediate irrigation is recommended for highland fruits. Check sensor calibration.")
            suggestions.append("Consider planting drought-resistant varieties if conditions persist.")
        elif avg_soil_moisture < 41:
            suggestions.append("Low soil moisture. Consider increasing irrigation frequency, especially for strawberries.")
            suggestions.append("Monitor weather conditions closely for potential rainfall.")
        elif avg_soil_moisture < 71:
            suggestions.append("Optimal soil moisture levels for highland fruits. Continue current irrigation practices.")
            suggestions.append("This is a good time for applying balanced fertilizers.")
        elif avg_soil_moisture < 86:
            suggestions.append("High soil moisture. Reduce irrigation frequency and ensure good drainage to prevent root rot.")
            suggestions.append("Monitor for diseases that thrive in moist conditions.")
        else:
            suggestions.append("Very high soil moisture! Take immediate actions to prevent root rot and potential crop loss.")
            suggestions.append("Consider organic mulching to help retain soil moisture in hot conditions.")

        # Button to generate report
        user_name = "Farmer John"  # Example user name, replace with actual input if necessary
        if st.button("Generate Report"):
            # Pass the chart images to the report generation function
            charts = [soil_moisture_chart_image, histogram_image, moving_average_chart_image]
            pdf_buffer = generate_pdf_report(sensor_data, avg_soil_moisture, suggestions, charts, user_name=user_name)
            st.download_button("Download PDF Report", pdf_buffer, "soil_moisture_report.pdf", "application/pdf")



# Real-Time Control functionality
def real_time_control():
    st.header("Real-Time Soil Moisture Monitoring and Pump Control")

    # Simulated real-time soil moisture data (replace with actual sensor integration)
    soil_moisture_level = st.slider("Current Soil Moisture Level", 0, 100, 50)
    water_pump_status = st.radio("Water Pump Status", ("ON", "OFF"))

    # Display current sensor data
    st.metric(label="Soil Moisture Level", value=f"{soil_moisture_level}%")
    st.metric(label="Water Pump Status", value=water_pump_status)

    # Manual water pump control
    if st.button("Turn Water Pump ON"):
        st.success("Water pump turned ON")
    elif st.button("Turn Water Pump OFF"):
        st.warning("Water pump turned OFF")

# Run the application
if __name__ == "__main__":
    main()
