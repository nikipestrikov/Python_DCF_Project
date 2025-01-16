import streamlit as st

# Function to calculate net land area based on plot type
def calculate_net_land_area(plot_size, is_parceled, road_deduction_percent, green_area_formula):
    if is_parceled:
        return plot_size, 0, 0
    else:
        road_deduction = plot_size * (road_deduction_percent / 100)
        after_road_deduction = plot_size - road_deduction
        green_deduction = green_area_formula(after_road_deduction)
        net_area = after_road_deduction - green_deduction
        return round(net_area), round(road_deduction), round(green_deduction)

# Green area deduction based on plot size
def green_area_formula(area):
    if area < 800:
        return 0
    elif 800 <= area < 1500:
        return area * 0.05
    elif 1500 <= area < 2500:
        return area * 0.10
    elif 2500 <= area < 10000:
        return area * 0.15
    elif 10000 <= area < 50000:
        return area * 0.17
    else:
        return area * 0.18

# Function to calculate total area and weighted densities
def calculate_totals(plots, apply_efficiency_incentive):
    total_net_area = 0
    total_road_deduction = 0
    total_green_deduction = 0
    commercial_area = 0
    residential_area = 0
    commercial_density_sum = 0
    residential_density_sum = 0

    for plot in plots:
        net_plot_size, road_deduction, green_deduction = calculate_net_land_area(
            plot["plot_size"],
            plot["is_parceled"],
            plot["road_deduction_percent"],
            green_area_formula
        )
        total_net_area += net_plot_size
        total_road_deduction += road_deduction
        total_green_deduction += green_deduction

        for zone in plot["zones"]:
            zone_area = net_plot_size * (zone["percentage"] / 100)
            density_factor = zone["density_factor"]
            density_type = zone["density_type"].lower()

            if density_type == "commercial":
                commercial_area += zone_area
                commercial_density_sum += zone_area * density_factor
            elif density_type == "residential":
                residential_area += zone_area
                residential_density_sum += zone_area * density_factor

    commercial_density_avg = (commercial_density_sum / commercial_area) if commercial_area else 0
    residential_density_avg = (residential_density_sum / residential_area) if residential_area else 0

    commercial_buildable_area = (commercial_area * commercial_density_avg) / 100
    residential_buildable_area = (residential_area * residential_density_avg) / 100

    incentive_area = 0
    if apply_efficiency_incentive:
        incentive_area = 0.05 * (commercial_buildable_area + residential_buildable_area)

    total_buildable_area = commercial_buildable_area + residential_buildable_area + incentive_area

    return {
        "total_net_area": round(total_net_area),
        "total_road_deduction": round(total_road_deduction),
        "total_green_deduction": round(total_green_deduction),
        "commercial_avg_density": round(commercial_density_avg),
        "residential_avg_density": round(residential_density_avg),
        "commercial_buildable_area": round(commercial_buildable_area),
        "residential_buildable_area": round(residential_buildable_area),
        "incentive_area": round(incentive_area),
        "total_buildable_area": round(total_buildable_area)
    }

# Streamlit UI
st.title("Real Estate Density Calculator")

st.sidebar.header("Plot Configuration")
num_plots = st.sidebar.number_input("Number of Plots", min_value=1, max_value=10, value=1, step=1)

apply_efficiency_incentive = st.sidebar.checkbox("Apply 5% Efficiency Incentive")
price_toggle = st.sidebar.radio("Specify Price For", ["Each Plot", "Total Project"])

total_price = 0
plots = []

if price_toggle == "Total Project":
    total_price = st.number_input("Total Project Price (€)", min_value=0, step=1, format="%d")

for i in range(num_plots):
    with st.sidebar.expander(f"Plot {i + 1} Configuration", expanded=False):
        serial_number = st.text_input(f"Plot {i + 1} Serial Number", value=f"Plot-{i + 1}", key=f"serial_{i}")
        plot_size = st.number_input(f"Plot {i + 1} Size (m²)", min_value=0, value=1000, step=1, format="%d", key=f"plot_size_{i}")
        is_parceled = st.checkbox(f"Is Plot {i + 1} Parceled?", value=True, key=f"parceled_{i}")
        road_deduction_percent = 0

        if not is_parceled:
            road_deduction_percent = st.slider(f"Plot {i + 1} Road Deduction (%)", min_value=0, max_value=50, value=10, step=1, key=f"road_{i}")

        num_zones = st.number_input(f"Number of Zones", min_value=1, max_value=3, value=1, step=1, key=f"zones_{i}")
        zones = []
        remaining_percentage = 100

        for j in range(int(num_zones)):
            percentage = st.slider(f"Zone {j + 1} %", min_value=0, max_value=remaining_percentage, value=remaining_percentage, step=1, key=f"zone_{i}_{j}")
            remaining_percentage -= percentage
            density_factor = st.number_input(f"Zone {j + 1} Density Factor (%)", min_value=0, value=50, step=1, key=f"density_{i}_{j}")
            density_type = st.selectbox(f"Zone {j + 1} Type", ["Residential", "Commercial"], key=f"type_{i}_{j}")
            zones.append({"percentage": percentage, "density_factor": density_factor, "density_type": density_type})

        plot_price = st.number_input(f"Price for Plot {i + 1}", min_value=0, step=1, format="%d", key=f"price_{i}") if price_toggle == "Each Plot" else 0
        total_price += plot_price

        plots.append({"serial_number": serial_number, "plot_size": plot_size, "is_parceled": is_parceled, "road_deduction_percent": road_deduction_percent, "zones": zones})

if st.button("Calculate"):
    results = calculate_totals(plots, apply_efficiency_incentive)
    price_per_m2 = total_price / results['total_buildable_area'] if results['total_buildable_area'] else 0
    st.success(f"**Price per Buildable m²:** {round(price_per_m2):,} €")
    st.subheader("Calculation Results")
    st.write(f"**Total Buildable Area:** {results['total_buildable_area']} m²")
    st.write(f"**Efficiency Incentive Area:** {results['incentive_area']} m²")
    st.write(f"**Commercial Buildable Area:** {results['commercial_buildable_area']} m²")
    st.write(f"**Residential Buildable Area:** {results['residential_buildable_area']} m²")
    st.write(f"**Road Deduction Area:** {results['total_road_deduction']} m²")
    st.write(f"**Green Deduction Area:** {results['total_green_deduction']} m²")
