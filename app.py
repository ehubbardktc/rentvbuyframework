# Rent v. Buy Decision Support Framework

# Import packages

import streamlit as st
import pandas as pd

# ----------------------------- INSTRUCTIONS -----------------------------------
st.set_page_config(page_title="Rent v. Buy Decision Support Framework", layout="wide")

st.title("Rent v. Buy Decision Support Framework")

st.expander("Welcome & Instructions", expanded=True).markdown(
    """
    This dashboard provides an analytical framework to provide data-driven support for your decision to rent or buy your primary residence. 
    Tables and visuals will update automatically with your selections.

    **Key Outputs:**
    - X
    - Y
    - Z

    **How to use:**
    
    *If on mobile, select ">>" arrows in the top left to open selection pane*

    1. Enter the sale price
    2. Enter loan details

    **Methodology:**
    
    - **Funds Available for Investing:** For modeling purposes, we assume that the difference in expenses between renting and buying will be fully invested.
    """
)

# --------------------------------- CONSTANTS -------------------------------------------
# Number of Months per Year
months = list(range(1, 13))

# Closing costs default values
default_closing_costs = pd.DataFrame({
    "Category": [
        "Initial Loan Costs", "Initial Loan Costs", "Initial Loan Costs", "Initial Loan Costs", 
        "Initial Loan Costs", "Initial Loan Costs", "Initial Loan Costs", "Initial Loan Costs", 
        "Initial Loan Costs", "Initial Loan Costs", 
        "Taxes & Fees", "Taxes & Fees",
        "Prepaids", "Prepaids", "Prepaids",
        "Escrow",
        "Other"
    ],
    "Item": [
        "Loan Processing Fee", "Underwriting Fee", "Appraisal Fee", "Credit Report Fee",
        "Flood Certificate Fee", "Mers Registration Fee", "Tax Service Fee", "Title - CPL Fee",
        "Title - Lending Title Insurance", "Title - Settlement/Closing Fee",
        "Recording Fees", "State Property Transfer Tax (Buyer Portion)",
        "Homeowners Insurance Premium (Annual up front)", "Prepaid Interest", "Property Taxes",
        "Mortgage Insurance",
        "Title-owner policy"
    ],
    "Amount ($)": [
        550, 800, 100, 25,
        5, 25, 70, 25,
        1250, 700,
        175, 4500,
        1200, 750, 250,
        150,
        500
    ]
})

# --------------------------------- SIDEBAR ---------------------------------------------
# Main UI sidebar
with st.sidebar:
    st.image("images/EyesWideOpenLogo.png", use_container_width=False, width=300)
    st.markdown("Tool developed by Eric Hubbard. More details about charging models, and more, by navigating to the URL below:")
    st.markdown("[Navigate to: KnowTheCostFinancial.com](https://knowthecostfinancial.com)")

    # Shared Inputs
    st.header("1. General Inputs")
    eval_start_year = st.number_input("Evaluation Start Year", value=2025)
    eval_end_year = st.number_input("Evaluation End Year", value=2070)
    # analysis_years = st.number_input("Analysis Period (Years)", value=end_year-start_year, step=1)
    initial_tax_brokerage_balance = st.number_input("Initial Taxable Brokerage Balance ($)", value=250000, step=10000)
    initial_tax_brokerage_balance = st.number_input("Average Annual Housing Appreciation", value=250000, step=10000)

    st.markdown("---")

    with st.expander("Housing Assumptions"):
        # st.header("2. Housing Assumptions")
        st.info("Set parameters specific to buying.")
        purchase_year = st.number_input("Purhcase Year", value = 2025, step = 1)
        purchase_price = st.number_input("Purchase Price ($)", value=500000, step=10000)
        down_payment = st.number_input("Down Payment ($)", value=60000, step=1000)
        # down_payment_perc = st.number_input("Down Payment %", value = down_payment/purchase_price, step = 0.01) # Make this visible in the bar, but not able to change
        st.subheader("Loan Terms")
        loan_length = st.number_input("Loan Length (Years)", value=30, step=5)
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.1)
        mortgage_years = st.number_input("Mortgage Term (Years)", value=30, step=1)
        pmi_paid_until_equity = st.number_input("PMI Paid Until What '%' Equity", value = 20, step = 1)
        pmi_rate = st.number_input("PMI Rate", value = .20, step = .01)
        # Advanced loan options
        # Add ability to refinance, specify year, etc.
        # Add ability to buy points to buy down rate (want to see the breakeven for when it makes financial sense to do that if buying)

        st.subheader("Closing Costs")
        edited_costs = st.sidebar.data_editor(
        default_closing_costs,
        use_container_width=True,
        num_rows="dynamic",  # enables the user to add/remove rows
        hide_index=True)

        st.subheader("Taxes")
        annual_property_tax = st.number_input("Annual Property Tax ($)", value=3500, step=100)
        annual_property_tax_increase = st.number_input("Annual Property Tax Increase (%)", value=3.0, step=0.1)
        state_property_transfer_tax = st.number_input("State Property Transfer Tax (%)", value=1.5, step=0.1)

    # Additional Mortgage Principal Payments; I MAY WANT TO PULL THIS OUT INTO ITS OWN TABLE OUTSIDE OF SIDEBAR
    st.sidebar.header("Extra Principal Payments")

    default_payments = pd.DataFrame({
        "Amount ($)": [200, 10000],
        "Start Year": [2025, 2030],
        "Start Month": [1, 6],
        "End Year": [2030, 2030],
        "End Month": [12, 6],
        "Frequency": ["Monthly", "One-time"]
    })

    # Dropdown options
    frequency_options = ["One-time", "Monthly", "Quarterly", "Annually", "Every X Years"]
    month_options = list(range(1, 13))
    year_options = list(range(2025, 2101))

    # Editable table with dropdowns
    edited_payments = st.data_editor(
        default_payments,
        column_config={
            "Frequency": st.column_config.SelectboxColumn("Frequency", options=frequency_options),
            "Start Month": st.column_config.SelectboxColumn("Start Month", options=month_options),
            "End Month": st.column_config.SelectboxColumn("End Month", options=month_options),
            "Start Year": st.column_config.SelectboxColumn("Start Year", options=year_options),
            "End Year": st.column_config.SelectboxColumn("End Year", options=year_options),
        },
        width="stretch",   # replaces use_container_width
        hide_index=True,
        num_rows="dynamic"
    )
    
    default_payments = default_payments[["Frequency","Amount ($)", "Start Year", "Start Month", "End Year", "End Month"]]

    st.markdown("---")

    with st.expander("Appreciation"):
        # st.subheader("Appreciation")
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=3.5, step=0.1)
        annual_maintenance_increase = st.number_input("Annual Regular Maintenance Increase (%)", value=3.0, step=0.1)
        annual_insurance_increase = st.number_input("Annual Homeowners Insurance Increase (%)", value=3.0, step=0.1)
    
    st.markdown("---")

    with st.expander("Rental Assumptions"):
        # st.header("3. Rental Assumptions")
        st.info("")
        cost_of_rent = st.sidebar.number_input("Cost of Rental Y0 ($)", value=3000, step=50) # Insert the beginning year here in the title
        annual_rent_increase = st.sidebar.number_input("Annual Rent Increase (%)", value=4.0, step=0.1)
        # rent_to_buy_ratio = st.sidebar.number_input("Rent-to-Buy Ratio", value=16.7, step=0.1)

    st.markdown("---")

    st.header("4. Investment (Taxable Brokerage Account) Assumptions")
    st.info("")
    annual_stock_return = st.sidebar.number_input("Annual Average Stock Market Return (%)", value=8.0, step=0.1)
    # monthly_stock_return = st.sidebar.number_input("Monthly Average Stock Market Return (%)", value=annual_stock_return/12, step=0.01)

    st.markdown("---")

    st.header("5. Monte Carlo Inputs")
    st.info("")
    mc_simulation_stock_mean = st.number_input("Simulation Stock Market Return Mean (%)", value=8.0, step=0.1)
    mc_simulation_stock_std = st.number_input("Simulation Stock Market Return Std. Dev. (%)", value=15.0, step=0.1)

    

