import streamlit as st
import pandas as pd
import numpy as np
from streamlit.components.v1 import html
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
import pickle
import io
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import base64
import json
import datetime
from pathlib import Path
from functions import *

# Set page config
st.set_page_config(layout="wide", page_title="Carbon Footprint Calculator", page_icon="./media/favicon.ico")

# Setup session state for user management
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "default_user"  # In a real app, this would come from authentication

if "show_dashboard" not in st.session_state:
    st.session_state["show_dashboard"] = False

# Function to save user data
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

# Functions to calculate impact by category
def calculate_travel_impact(data):
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
    base = 80
    if data.get("Heating Energy Source") == "coal":
        base += 200
    elif data.get("Heating Energy Source") == "natural gas":
        base += 100
    base += data.get("How Long TV PC Daily Hour", 0) * 5
    return base

def calculate_consumption_impact(data):
    base = 50
    base += data.get("Monthly Grocery Bill", 0) * 0.5
    base += data.get("How Many New Clothes Monthly", 0) * 10
    return base

def calculate_waste_impact(data):
    base = 30
    if data.get("Waste Bag Size") == "extra large":
        base += 100
    elif data.get("Waste Bag Size") == "large":
        base += 70
    elif data.get("Waste Bag Size") == "medium":
        base += 40
    base += data.get("Waste Bag Weekly Count", 0) * 20
    recycle_count = sum(1 for k in data.keys() if k.startswith("Do You Recyle_") and data[k] == 1)
    base -= recycle_count * 15
    return max(base, 0)

def calculate_diet_impact(data):
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
    
    if data.get("Transport") == "private" and data.get("Vehicle Monthly Distance Km", 0) > 500:
        recommendations.append("Consider using public transport more often to reduce your carbon footprint.")
    
    if data.get("Frequency of Traveling by Air") in ["frequently", "very frequently"]:
        recommendations.append("Reduce air travel or consider carbon offset programs for unavoidable flights.")
    
    if data.get("Heating Energy Source") in ["coal", "natural gas"]:
        recommendations.append("Consider switching to renewable energy sources for heating.")
    
    if data.get("How Long TV PC Daily Hour", 0) > 6:
        recommendations.append("Reduce screen time to save energy and lower your carbon footprint.")
    
    if data.get("How Many New Clothes Monthly", 0) > 5:
        recommendations.append("Try to buy fewer new clothes or shop second-hand to reduce your carbon footprint.")
    
    if data.get("Waste Bag Weekly Count", 0) > 3:
        recommendations.append("Try to reduce your waste by composting food scraps and buying products with less packaging.")
    
    recycle_count = sum(1 for k in data.keys() if k.startswith("Do You Recyle_") and data[k] == 1)
    if recycle_count < 2:
        recommendations.append("Increase your recycling efforts to reduce your carbon footprint.")
    
    if data.get("Diet") == "omnivore":
        recommendations.append("Consider reducing meat consumption to lower your carbon footprint.")
    
    return recommendations

# User dashboard function
def user_dashboard():
    user_id = st.session_state.get("user_id", "default_user")
    
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
    
    # Breakdown of the latest footprint
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

# Original CSS and styling code
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

background = get_base64("./media/background_min.jpg")
icon2 = get_base64("./media/icon2.png")
icon3 = get_base64("./media/icon3.png")

with open("./style/style.css", "r") as style:
    css=f"""<style>{style.read().format(background=background, icon2=icon2, icon3=icon3)}</style>"""
    st.markdown(css, unsafe_allow_html=True)

def script():
    with open("./style/scripts.js", "r", encoding="utf-8") as scripts:
        open_script = f"""<script>{scripts.read()}</script> """
        html(open_script, width=0, height=0)

# Add a navigation sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Calculator", "Dashboard"])

if page == "Calculator":
    # Original app layout
    left, middle, right = st.columns([2,3.5,2])
    main, comps, result = middle.tabs([" ", " ", " "])

    with open("./style/main.md", "r", encoding="utf-8") as main_page:
        main.markdown(f"""{main_page.read()}""")

    _,but,_ = main.columns([1,2,1])
    if but.button("Calculate Your Carbon Footprint!", type="primary"):
        click_element('tab-1')

    tab1, tab2, tab3, tab4, tab5 = comps.tabs(["👴 Personal","🚗 Travel","🗑️ Waste","⚡ Energy","💸 Consumption"])
    tab_result,_ = result.tabs([" "," "])

    # Original component function with added save functionality
    def component():
        tab1col1, tab1col2 = tab1.columns(2)
        height = tab1col1.number_input("Height",0,251, value=None, placeholder="160", help="in cm")
        weight = tab1col2.number_input("Weight", 0, 250, value=None, placeholder="75", help="in kg")
        if (weight is None) or (weight == 0) : weight = 1
        if (height is None) or (height == 0) : height = 1
        calculation = weight / (height/100)**2
        body_type = "underweight" if (calculation < 18.5) else \
                    "normal" if ((calculation >=18.5) and (calculation < 25 )) else \
                    "overweight" if ((calculation >= 25) and (calculation < 30)) else "obese"
        sex = tab1.selectbox('Gender', ["female", "male"])
        diet = tab1.selectbox('Diet', ['omnivore', 'pescatarian', 'vegetarian', 'vegan'], help="""
                                                                                                Omnivore: Eats both plants and animals.\n
                                                                                                Pescatarian: Consumes plants and seafood, but no other meat\n
                                                                                                Vegetarian: Diet excludes meat but includes plant-based foods.\n
                                                                                                Vegan: Avoids all animal products, including meat, dairy, and eggs.""")
        social = tab1.selectbox('Social Activity', ['never', 'often', 'sometimes'], help="How often do you go out?")

        transport = tab2.selectbox('Transportation', ['public', 'private', 'walk/bicycle'],
                                help="Which transportation method do you prefer the most?")
        if transport == "private":
            vehicle_type = tab2.selectbox('Vehicle Type', ['petrol', 'diesel', 'hybrid', 'lpg', 'electric'],
                                        help="What type of fuel do you use in your car?")
        else:
            vehicle_type = "None"

        if transport == "walk/bicycle":
            vehicle_km = 0
        else:
            vehicle_km = tab2.slider('What is the monthly distance traveled by the vehicle in kilometers?', 0, 5000, 0, disabled=False)

        air_travel = tab2.selectbox('How often did you fly last month?', ['never', 'rarely', 'frequently', 'very frequently'], help= """
                                                                                                                                Never: I didn't travel by plane.\n
                                                                                                                                Rarely: Around 1-4 Hours.\n
                                                                                                                                Frequently: Around 5 - 10 Hours.\n
                                                                                                                                Very Frequently: Around 10+ Hours. """)

        waste_bag = tab3.selectbox('What is the size of your waste bag?', ['small', 'medium', 'large', 'extra large'])
        waste_count = tab3.slider('How many waste bags do you trash out in a week?', 0, 10, 0)
        recycle = tab3.multiselect('Do you recycle any materials below?', ['Plastic', 'Paper', 'Metal', 'Glass'])

        heating_energy = tab4.selectbox('What power source do you use for heating?', ['natural gas', 'electricity', 'wood', 'coal'])

        for_cooking = tab4.multiselect('What cooking systems do you use?', ['microwave', 'oven', 'grill', 'airfryer', 'stove'])
        energy_efficiency = tab4.selectbox('Do you consider the energy efficiency of electronic devices?', ['No', 'Yes', 'Sometimes' ])
        daily_tv_pc = tab4.slider('How many hours a day do you spend in front of your PC/TV?', 0, 24, 0)
        internet_daily = tab4.slider('What is your daily internet usage in hours?', 0, 24, 0)

        shower = tab5.selectbox('How often do you take a shower?', ['daily', 'twice a day', 'more frequently', 'less frequently'])
        grocery_bill = tab5.slider('Monthly grocery spending in $', 0, 500, 0)
        clothes_monthly = tab5.slider('How many clothes do you buy monthly?', 0, 30, 0)

        data = {'Body Type': body_type,
                "Sex": sex,
                'Diet': diet,
                "How Often Shower": shower,
                "Heating Energy Source": heating_energy,
                "Transport": transport,
                "Social Activity": social,
                'Monthly Grocery Bill': grocery_bill,
                "Frequency of Traveling by Air": air_travel,
                "Vehicle Monthly Distance Km": vehicle_km,
                "Waste Bag Size": waste_bag,
                "Waste Bag Weekly Count": waste_count,
                "How Long TV PC Daily Hour": daily_tv_pc,
                "Vehicle Type": vehicle_type,
                "How Many New Clothes Monthly": clothes_monthly,
                "How Long Internet Daily Hour": internet_daily,
                "Energy efficiency": energy_efficiency
                }
        data.update({f"Cooking_with_{x}": y for x, y in
                    dict(zip(for_cooking, np.ones(len(for_cooking)))).items()})
        data.update({f"Do You Recyle_{x}": y for x, y in
                    dict(zip(recycle, np.ones(len(recycle)))).items()})

        return pd.DataFrame(data, index=[0])

    df = component()
    data = input_preprocessing(df)

    sample_df = pd.DataFrame(data=sample,index=[0])
    sample_df[sample_df.columns] = 0
    sample_df[data.columns] = data

    ss = pickle.load(open("./models/scale.sav","rb"))
    model = pickle.load(open("./models/model.sav","rb"))
    prediction = round(np.exp(model.predict(ss.transform(sample_df))[0]))

    column1,column2 = tab1.columns(2)
    _,resultbutton,_ = tab5.columns([1,1,1])
    
    # Add save to dashboard button
    _, save_col, _ = tab5.columns([1,1,1])
    if save_col.button("Save to Dashboard"):
        tree_count = round(prediction / 411.4)
        user_history = save_user_data(st.session_state["user_id"], data, prediction, tree_count)
        st.success("Data saved to your dashboard successfully!")
    
    if resultbutton.button(" ", type = "secondary"):
        tab_result.image(chart(model,ss, sample_df,prediction), use_column_width="auto")
        click_element('tab-2')

    pop_button = """<button id = "button-17" class="button-17" role="button"> ❔ Did You Know</button>"""
    _,home,_ = comps.columns([1,2,1])
    _,col2,_ = comps.columns([1,10,1])
    col2.markdown(pop_button, unsafe_allow_html=True)
    pop = """
    <div id="popup" class="DidYouKnow_root">
    <p class="DidYouKnow_title TextNew" style="font-size: 20px;"> ❔ Did you know</p>
        <p id="popupText" class="DidYouKnow_content TextNew"><span>
        Each year, human activities release over 40 billion metric tons of carbon dioxide into the atmosphere, contributing to climate change.
        </span></p>
    </div>
    """
    col2.markdown(pop, unsafe_allow_html=True)

    if home.button("🏡"):
        click_element('tab-0')
    _,resultmid,_ = result.columns([1,2,1])

    tree_count = round(prediction / 411.4)
    tab_result.markdown(f"""You owe nature <b>{tree_count}</b> tree{'s' if tree_count > 1 else ''} monthly. <br> {f"<a href='https://www.tema.org.tr/en/homepage' id = 'button-17' class='button-17' role='button'> 🌳 Proceed to offset 🌳</a>" if tree_count > 0 else ""}""",  unsafe_allow_html=True)

    if resultmid.button("  ", type="secondary"):
        click_element('tab-1')

elif page == "Dashboard":
    # Display user dashboard
    user_dashboard()

# Footer
with open("./style/footer.html", "r", encoding="utf-8") as footer:
    footer_html = f"""{footer.read()}"""
    st.markdown(footer_html, unsafe_allow_html=True)

script()