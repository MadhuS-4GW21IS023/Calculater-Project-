import streamlit as st
import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt
import datetime
import json
from pathlib import Path
from functions import input_preprocessing, chart, click_element

# This function will save the user's carbon footprint data to a JSON file
def save_user_data(user_id, data, prediction, tree_count):
    # Create a folder for user data if it doesn't exist
    Path("./user_data").mkdir(exist_ok=True)
    
    # Get today's date for the record
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Prepare data for saving
    user_record = {
        "date": today,
        "carbon_footprint": int(prediction),
        "trees_owed": int(tree_count),
        "input_data": data.to_dict(orient="records")[0]
    }
    
    # Load existing records or create new
    user_file = Path(f"./user_data/{user_id}.json")
    if user_file.exists():
        with open(user_file, "r") as f:
            user_history = json.load(f)
    else:
        user_history = {"history": []}
    
    # Add the new record
    user_history["history"].append(user_record)
    
    # Save back to file
    with open(user_file, "w") as f:
        json.dump(user_history, f, indent=4)
    
    return user_history

# Function to create a user dashboard
def user_dashboard(user_id):
    st.markdown("## Carbon Footprint Dashboard")
    
    # Check if the user has data
    user_file = Path(f"./user_data/{user_id}.json")
    if not user_file.exists():
        st.warning("No carbon footprint data available. Please calculate your footprint first.")
        return
    
    # Load user history
    with open(user_file, "r") as f:
        user_history = json.load(f)
    
    # Convert to DataFrame for easier processing
    df_history = pd.DataFrame([record for record in user_history["history"]])
    
    # Layout
    col1, col2 = st.columns(2)
    
    # Latest footprint information
    latest = user_history["history"][-1]
    col1.metric("Your Latest Carbon Footprint", f"{latest['carbon_footprint']} kg CO₂", 
                delta=f"{latest['carbon_footprint'] - user_history['history'][-2]['carbon_footprint']} kg" 
                if len(user_history["history"]) > 1 else None)
    
    col2.metric("Trees Owed", latest["trees_owed"],
                delta=f"{latest['trees_owed'] - user_history['history'][-2]['trees_owed']}" 
                if len(user_history["history"]) > 1 else None)
    
    # Historical trend chart
    st.subheader("Carbon Footprint Over Time")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_history["date"], df_history["carbon_footprint"], marker='o', linestyle='-')
    ax.set_xlabel("Date")
    ax.set_ylabel("Carbon Footprint (kg CO₂)")
    ax.grid(True)
    st.pyplot(fig)
    
    # Breakdown of the latest footprint (simplified categories)
    st.subheader("Footprint Breakdown")
    categories = {
        "Travel": calculate_travel_impact(latest["input_data"]),
        "Energy": calculate_energy_impact(latest["input_data"]),
        "Consumption": calculate_consumption_impact(latest["input_data"]),
        "Waste": calculate_waste_impact(latest["input_data"]),
        "Diet": calculate_diet_impact(latest["input_data"])
    }
    
    # Create a pie chart of the breakdown
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)
    
    # Recommendations based on their footprint
    st.subheader("Recommendations to Reduce Your Footprint")
    recommendations = generate_recommendations(latest["input_data"])
    for rec in recommendations:
        st.markdown(f"- {rec}")
    
    # Historical data table
    st.subheader("History")
    st.dataframe(df_history[["date", "carbon_footprint", "trees_owed"]])

# Example functions to calculate impacts for each category
# In a real implementation, you would need more sophisticated calculations
def calculate_travel_impact(data):
    # This would use your model to estimate just the travel portion
    # Simplified example:
    base = 100
    if data.get("Transport") == "private":
        base += data.get("Vehicle Monthly Distance Km", 0) * 0.2
    if data.get("Frequency of Traveling by Air") == "very frequently":
        base += 500
    elif data.get("Frequency of Traveling by Air") == "frequently":
        base += 300
    elif data.get("Frequency of Traveling by Air") == "rarely":
        base += 100
    return base

def calculate_energy_impact(data):
    # Simplified example:
    base = 80
    if data.get("Heating Energy Source") == "coal":
        base += 200
    elif data.get("Heating Energy Source") == "natural gas":
        base += 100
    base += data.get("How Long TV PC Daily Hour", 0) * 5
    return base

def calculate_consumption_impact(data):
    # Simplified example:
    base = 50
    base += data.get("Monthly Grocery Bill", 0) * 0.5
    base += data.get("How Many New Clothes Monthly", 0) * 10
    return base

def calculate_waste_impact(data):
    # Simplified example:
    base = 30
    if data.get("Waste Bag Size") == "extra large":
        base += 100
    elif data.get("Waste Bag Size") == "large":
        base += 70
    elif data.get("Waste Bag Size") == "medium":
        base += 40
    base += data.get("Waste Bag Weekly Count", 0) * 20
    # Reduce based on recycling
    recycle_count = sum(1 for k in data.keys() if k.startswith("Do You Recyle_") and data[k] == 1)
    base -= recycle_count * 15
    return max(base, 0)  # ensure it doesn't go negative

def calculate_diet_impact(data):
    # Simplified example:
    if data.get("Diet") == "vegan":
        return 50
    elif data.get("Diet") == "vegetarian":
        return 100
    elif data.get("Diet") == "pescatarian":
        return 150
    else:  # omnivore
        return 200

def generate_recommendations(data):
    recommendations = []
    
    # Travel recommendations
    if data.get("Transport") == "private" and data.get("Vehicle Monthly Distance Km", 0) > 500:
        recommendations.append("Consider using public transport more often to reduce your carbon footprint.")
    
    if data.get("Frequency of Traveling by Air") in ["frequently", "very frequently"]:
        recommendations.append("Reduce air travel or consider carbon offset programs for unavoidable flights.")
    
    # Energy recommendations
    if data.get("Heating Energy Source") in ["coal", "natural gas"]:
        recommendations.append("Consider switching to renewable energy sources for heating.")
    
    if data.get("How Long TV PC Daily Hour", 0) > 6:
        recommendations.append("Reduce screen time to save energy and lower your carbon footprint.")
    
    # Consumption recommendations
    if data.get("How Many New Clothes Monthly", 0) > 5:
        recommendations.append("Try to buy fewer new clothes or shop second-hand to reduce your carbon footprint.")
    
    # Waste recommendations
    if data.get("Waste Bag Weekly Count", 0) > 3:
        recommendations.append("Try to reduce your waste by composting food scraps and buying products with less packaging.")
    
    recycle_count = sum(1 for k in data.keys() if k.startswith("Do You Recyle_") and data[k] == 1)
    if recycle_count < 2:
        recommendations.append("Increase your recycling efforts to reduce your carbon footprint.")
    
    # Diet recommendations
    if data.get("Diet") == "omnivore":
        recommendations.append("Consider reducing meat consumption to lower your carbon footprint.")
    
    return recommendations

# Modify your existing component function to add a save button and user dashboard link
def modified_component():
    # Use the existing component function to collect data
    df = component()
    data = input_preprocessing(df)
    
    sample_df = pd.DataFrame(data=sample,index=[0])
    sample_df[sample_df.columns] = 0
    sample_df[data.columns] = data
    
    ss = pickle.load(open("./models/scale.sav","rb"))
    model = pickle.load(open("./models/model.sav","rb"))
    prediction = round(np.exp(model.predict(ss.transform(sample_df))[0]))
    tree_count = round(prediction / 411.4)
    
    # Add a login or user identification system
    user_id = st.session_state.get("user_id", "default_user")
    
    # Add a save button
    if st.button("Save to My Dashboard"):
        user_history = save_user_data(user_id, data, prediction, tree_count)
        st.success("Data saved to your dashboard successfully!")
    
    # Add a link to the dashboard
    if st.button("View My Dashboard"):
        st.session_state["show_dashboard"] = True
    
    return df, prediction, tree_count

# Integrate with the main app
def main():
    # Setup session state
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = "default_user"  # In a real app, this would come from authentication
    
    if "show_dashboard" not in st.session_state:
        st.session_state["show_dashboard"] = False
    
    # Simple navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Calculator", "Dashboard"])
    
    if page == "Calculator":
        # Your existing app code here
        # ...
        
        # Replace your component call with modified_component
        df, prediction, tree_count = modified_component()
        
        # Rest of your calculator UI
        # ...
        
    elif page == "Dashboard":
        # Show the dashboard
        user_dashboard(st.session_state["user_id"])

if __name__ == "__main__":
    main()