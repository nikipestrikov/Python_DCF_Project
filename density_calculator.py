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
        return net_area, road_deduction, green_deduction


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
def calculate_totals(plots):
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

        zone_percentage_sum = sum(zone["percentage"] for zone in plot["zones"])
        if zone_percentage_sum > 100:
            st.warning(f"Zone percentages for {plot['serial_number']} exceed 100%. Please adjust.")
            continue

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

    return {
        "total_net_area": total_net_area,
        "total_road_deduction": total_road_deduction,
        "total_green_deduction": total_green_deduction,
        "commercial_avg_density": round(commercial_density_avg, 2),
        "residential_avg_density": round(residential_density_avg, 2),
        "commercial_buildable_area": round(commercial_buildable_area, 2),
        "residential_buildable_area": round(residential_buildable_area, 2)
    }


# Streamlit UI
st.title("Real Estate Density Calculator")

st.sidebar.header("Plot Configuration")
num_plots = st.sidebar.number_input("Number of Plots", min_value=1, max_value=10, value=1)

plots = []

for i in range(num_plots):
    st.sidebar.subheader(f"Plot {i + 1}")
    serial_number = st.sidebar.text_input(f"Plot {i + 1} Serial Number", value=f"Plot-{i + 1}")
    plot_size = st.sidebar.number_input(f"Plot {i + 1} Size (m²)", min_value=0.0, value=1000.0)
    is_parceled = st.sidebar.checkbox(f"Is Plot {i + 1} Parceled?", value=True)
    road_deduction_percent = 0

    if not is_parceled:
        road_deduction_percent = st.sidebar.slider(f"Plot {i + 1} Road Deduction (%)", min_value=0, max_value=50,
                                                   value=10)

    num_zones = st.sidebar.number_input(f"Number of Zones in Plot {i + 1}", min_value=1, max_value=3, value=1)

    zones = []
    remaining_percentage = 100

    for j in range(int(num_zones)):
        st.sidebar.markdown(f"**Zone {j + 1}**")
        max_percentage = remaining_percentage if j < num_zones - 1 else remaining_percentage
        percentage = st.sidebar.slider(f"Zone {j + 1} % of Plot {i + 1}", min_value=0, max_value=max_percentage,
                                       value=max_percentage)
        remaining_percentage -= percentage

        density_factor = st.sidebar.number_input(f"Zone {j + 1} Density Factor (%) in Plot {i + 1}", min_value=0.0,
                                                 value=50.0)
        density_type = st.sidebar.selectbox(f"Zone {j + 1} Type in Plot {i + 1}", ["Residential", "Commercial"])

        zones.append({
            "percentage": percentage,
            "density_factor": density_factor,
            "density_type": density_type
        })

    plots.append({
        "serial_number": serial_number,
        "plot_size": plot_size,
        "is_parceled": is_parceled,
        "road_deduction_percent": road_deduction_percent,
        "zones": zones
    })

if st.button("Calculate"):
    results = calculate_totals(plots)
    st.subheader("Calculation Results")
    st.write(f"**Total Net Land Area:** {results['total_net_area']} m²")
    st.write(f"**Total Road Deduction:** {results['total_road_deduction']} m²")
    st.write(f"**Total Public Green Deduction:** {results['total_green_deduction']} m²")
    st.write(f"**Weighted Commercial Density:** {results['commercial_avg_density']} %")
    st.write(f"**Weighted Residential Density:** {results['residential_avg_density']} %")
    st.write(f"**Commercial Buildable Area:** {results['commercial_buildable_area']} m²")
    st.write(f"**Residential Buildable Area:** {results['residential_buildable_area']} m²")
