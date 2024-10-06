import pandas as pd
import streamlit as st
import math

# Barlow's equation for calculating pressure
def Barlow(S, D, t):
    P = (2 * S * t) / D
    return P

# Streamlit input function to get user inputs
def get_user_inputs1():
    pressure = st.number_input("Enter the pressure (bar):", min_value=0.0, format="%.2f")
    temperature = st.number_input("Enter the temperature (°C):", min_value=0.0, format="%.2f")
    medium = st.text_input("Enter the medium (e.g., steam, water-glycol):")
    return pressure, temperature, medium

# Choose pipe material based on inputs
def choose_pipe_material(P, T, M):
    if M.lower() in ('water glycol', 'water-glycol', 'pressurized water', 'pressurized-water'):
        if P > 10 and T > 425:
            return 'B1005'
        else:
            return 'B1008'

    if P <= 10:
        if T <= 60:
            return 'B1008'
        elif 60 <= T <= 425:
            return 'B1001'
        else:
            return 'B1008'
    else:
        if T <= 425:
            return 'B1001'
        else:
            return 'B1005'

    if M.lower() in ('steam', 'thermal oil', 'thermal-oil'):
        return material
    else:
        if M.lower() in ('water glycol', 'water-glycol', 'pressurized water', 'pressurized-water'):
            return 'B1008' if material != 'B1005' else material

# Function to filter pipes based on pressure from B1001
def B1001_filter(P, file_path='B1001.csv'):
    df = pd.read_csv(file_path)
    df_split = df['Nominal diameter in inches;External diameter in mm;Wall thickness in mm;Weight in kg/m;Cost per 100 m in Euro\'s;Pressure in bar'].str.split(';', expand=True)
    df_split.columns = ['Nominal diameter (inches)', 'External diameter (mm)', 'Wall thickness (mm)', 'Weight (kg/m)', 'Cost per 100 m (Euro)', 'Pressure (bar)']
    df_split['External diameter (mm)'] = pd.to_numeric(df_split['External diameter (mm)'])
    df_split['Wall thickness (mm)'] = pd.to_numeric(df_split['Wall thickness (mm)'])
    df_split['Cost per 100 m (Euro)'] = pd.to_numeric(df_split['Cost per 100 m (Euro)'])
    df_split['Pressure (bar)'] = pd.to_numeric(df_split['Pressure (bar)'])
    df_split['Cost per m (Euro)'] = df_split['Cost per 100 m (Euro)'] / 100

    available_pipes = df_split[df_split['Pressure (bar)'] >= P]
    if available_pipes.empty:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available carbon steel pipes for {P} bar or higher pressure:")
        st.dataframe(available_pipes[['External diameter (mm)', 'Wall thickness (mm)', 'Cost per m (Euro)']])

# Function to filter pipes based on pressure from B1003
def B1003_filter(P, file_path='B1003.csv'):
    df = pd.read_csv(file_path)
    df_split = df['Nominal diameter in inches;Outside diameter in mm;Wall thickness in mm;Weight in kg/m;Cost per 100 m;Pressure in bar'].str.split(';', expand=True)
    df_split.columns = ['Nominal diameter (inches)', 'External diameter (mm)', 'Wall thickness (mm)', 'Weight (kg/m)', 'Cost per 100 m (Euro)', 'Pressure (bar)']
    df_split['External diameter (mm)'] = pd.to_numeric(df_split['External diameter (mm)'])
    df_split['Wall thickness (mm)'] = pd.to_numeric(df_split['Wall thickness (mm)'])
    df_split['Cost per 100 m (Euro)'] = pd.to_numeric(df_split['Cost per 100 m (Euro)'])
    df_split['Pressure (bar)'] = pd.to_numeric(df_split['Pressure (bar)'])
    df_split['Cost per m (Euro)'] = df_split['Cost per 100 m (Euro)'] / 100

    available_pipes = df_split[df_split['Pressure (bar)'] >= P]
    if available_pipes.empty:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available extra strong carbon steel pipes for {P} bar or higher pressure:")
        st.dataframe(available_pipes[['External diameter (mm)', 'Wall thickness (mm)', 'Cost per m (Euro)']])

# Function to filter pipes based on pressure from B1005
def B1005_filter(P, file_path='B1005.csv'):
    df = pd.read_csv(file_path)
    df_split = df['Nominal diameter in inches;Outside diameter in mm;Wall thickness in mm;Weight in kg/m;Cost per m (304 L);Cost per m (316 L);Pressure in bar'].str.split(';', expand=True)
    df_split.columns = ['Nominal diameter (inches)', 'External diameter (mm)', 'Wall thickness (mm)', 'Weight (kg/m)', 'Cost per m04 (Euro)', 'Cost per m16 (Euro)', 'Pressure (bar)']
    df_split['External diameter (mm)'] = pd.to_numeric(df_split['External diameter (mm)'])
    df_split['Wall thickness (mm)'] = pd.to_numeric(df_split['Wall thickness (mm)'])
    df_split['Cost per m (Euro)'] = pd.to_numeric(df_split['Cost per m04 (Euro)'])
    df_split['Pressure (bar)'] = pd.to_numeric(df_split['Pressure (bar)'])

    available_pipes = df_split[df_split['Pressure (bar)'] >= P]
    if available_pipes.empty:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available stainless steel pipes for {P} bar or higher pressure:")
        st.dataframe(available_pipes[['External diameter (mm)', 'Wall thickness (mm)', 'Cost per m (Euro)']])

# Function to filter pipes based on pressure from B1008
def B1008_filter(P, file_path='B1008.csv'):
    df = pd.read_csv(file_path)
    df_split = df['Outside Diameter (mm);Wall Thickness (mm);Working Pressure (bar);Cost per 100 m'].str.split(';', expand=True)
    df_split.columns = ['External diameter (mm)', 'Wall thickness (mm)', 'Pressure (bar)', 'Cost per 100 m (Euro)']
    df_split['External diameter (mm)'] = pd.to_numeric(df_split['External diameter (mm)'])
    df_split['Wall thickness (mm)'] = pd.to_numeric(df_split['Wall thickness (mm)'])
    df_split['Cost per 100 m (Euro)'] = pd.to_numeric(df_split['Cost per 100 m (Euro)'])
    df_split['Pressure (bar)'] = pd.to_numeric(df_split['Pressure (bar)'])
    df_split['Cost per m (Euro)'] = df_split['Cost per 100 m (Euro)'] / 100

    available_pipes = df_split[df_split['Pressure (bar)'] >= P]
    if available_pipes.empty:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available PVC pipes for {P} bar or higher pressure:")
        st.dataframe(available_pipes[['External diameter (mm)', 'Wall thickness (mm)', 'Cost per m (Euro)']])

# Function to choose and display available pipes
def Pipe_finder(material, P):
    if material == 'B1001':
        B1001_filter(P, file_path='B1001.csv')
    elif material == 'B1003':
        B1003_filter(P, file_path='B1003.csv')
    elif material == 'B1005':
        B1005_filter(P, file_path='B1005.csv')
    elif material == 'B1008':
        B1008_filter(P, file_path='B1008.csv')
    else:
        st.write("Material not found")

# Main function for the Streamlit app
def pipe_main():
    st.title("Pipe Selection Tool")
    
    # Get user inputs
    P, T, M = get_user_inputs1()
    
    if st.button("Find Pipe"):
        # Choose pipe material based on inputs
        Pipe_Material = choose_pipe_material(P, T, M)
        st.write(f"Chosen pipe material: {Pipe_Material}")
        
        # Find and display the available pipes
        Pipe_finder(Pipe_Material, P)

if __name__ == '__main__':
    pipe_main()
