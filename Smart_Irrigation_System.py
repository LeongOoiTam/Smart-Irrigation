import streamlit as st
import pandas as pd
import altair as alt
import os

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

# Helper function to load maintenance tasks
def load_maintenance_tasks():
    if os.path.exists('maintenance_tasks.csv'):
        return pd.read_csv('maintenance_tasks.csv')
    else:
        return pd.DataFrame(columns=['Task', 'Due Date', 'Assigned Worker', 'Status'])

# Helper function to save maintenance tasks
def save_maintenance_tasks(tasks_df):
    tasks_df.to_csv('maintenance_tasks.csv', index=False)

# Title of the application
st.title("Smart Fertigation Business System")

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

    # Admin Dashboard
    if role == "Admin":
        st.header("Admin Dashboard")
        # KPIs: System Health, Sales, Revenue
        st.subheader("Key Performance Indicators (KPIs)")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="System Health", value="Good")
        kpi2.metric(label="Total Sales (RM)", value="15,000")
        kpi3.metric(label="Revenue Streams (RM)", value="22,000")

        # Display upcoming maintenance tasks
        st.subheader("Upcoming Maintenance")
        maintenance_data = load_maintenance_tasks()
        st.table(maintenance_data)

        # Display Sales & Licensing Data
        st.subheader("Sales & Licensing")
        sales_data = pd.DataFrame({
            'Service': ['System Sales', 'Subscription', 'Licensing'],
            'Revenue': [10000, 5000, 2000]
        })
        total_revenue = sales_data['Revenue'].sum()
        st.bar_chart(sales_data.set_index('Service'))
        st.write(f"Total Revenue: RM {total_revenue}")

    # Sensor Data Monitoring (for Farmers/Clients)
    if role == "Farmer/Client":
        st.header("Sensor Data Monitoring")
        uploaded_file = st.file_uploader("Upload Sensor Data (CSV)", type="csv")

        if uploaded_file:
            sensor_data = pd.read_csv(uploaded_file)
            st.write(sensor_data)
            
            # Visualization: Water and Nutrient Levels
            water_chart = alt.Chart(sensor_data).mark_line().encode(
                x='Date:T',
                y='Water_Level:Q',
                color='Sensor:N'
            ).properties(title="Water Level Monitoring")
            nutrient_chart = alt.Chart(sensor_data).mark_line().encode(
                x='Date:T',
                y='Nutrient_Level:Q',
                color='Sensor:N'
            ).properties(title="Nutrient Level Monitoring")
            
            st.altair_chart(water_chart, use_container_width=True)
            st.altair_chart(nutrient_chart, use_container_width=True)

    # Maintenance Requests (for Workers)
    if role == "Maintenance Worker":
        st.header("Maintenance Requests")
        maintenance_tasks = load_maintenance_tasks()

        available_tasks = maintenance_tasks[maintenance_tasks['Status'] == 'Pending']
        if not available_tasks.empty:
            st.write("Available Jobs:")
            st.table(available_tasks)

            job_to_accept = st.selectbox("Select a job to accept", available_tasks['Task'])
            if st.button("Accept Job"):
                maintenance_tasks.loc[maintenance_tasks['Task'] == job_to_accept, 'Assigned Worker'] = auth_user
                maintenance_tasks.loc[maintenance_tasks['Task'] == job_to_accept, 'Status'] = 'In Progress'
                save_maintenance_tasks(maintenance_tasks)
                st.success(f"Job '{job_to_accept}' accepted successfully!")

        else:
            st.write("No pending jobs available.")

    # Training & Workshop (All Users)
    st.subheader("Training & Workshop Bookings")
    training_schedule = pd.DataFrame({
        'Session': ['Fertigation Basics', 'Advanced Monitoring'],
        'Date': ['2024-11-05', '2024-11-20'],
        'Slots Available': [5, 2]
    })
    st.table(training_schedule)

    st.write("Book your training slot:")
    session = st.selectbox("Choose a session", training_schedule['Session'])
    if st.button("Book Training"):
        st.success(f"Training booked for {session}")

else:
    if auth_user or auth_pass:
        st.sidebar.error("Invalid username or password!")