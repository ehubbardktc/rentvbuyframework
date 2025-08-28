# Rent v. Buy Decision Support Framework

# Import packages

import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf

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
with st.sidebar:
    st.image("images/EyesWideOpenLogo.png", width=300)
    st.markdown("Tool developed by Eric Hubbard. More details at:")
    st.markdown("[KnowTheCostFinancial.com](https://knowthecostfinancial.com)")

    # ---------------- General Inputs ----------------
    st.header("1. General Inputs")
    eval_start_year = st.number_input("Evaluation Start Year", value=2025, step=1)
    eval_end_year = st.number_input("Evaluation End Year", value=2070, step=1)

    st.markdown("---")

    # ---------------- Housing Assumptions ----------------

    st.header("2. Advanced Inputs")

    with st.expander("🏠 Housing Assumptions", expanded=False):
        st.info("Set parameters specific to buying.")

        purchase_year = st.number_input("Purchase Year", value=2025, step=1)
        purchase_price = st.number_input("Purchase Price ($)", value=500000, step=10000)
        down_payment = st.number_input("Down Payment ($)", value=60000, step=1000)

        # Market Assumptions
        st.subheader("Appreciation")
        avg_annual_appreciation = st.number_input("Average Annual Housing Appreciation (%)", value=3.5, step=0.1)

        # Loan Terms
        st.subheader("Loan Terms")
        loan_amount = purchase_price - down_payment # This is derived, no need to display in the sidebar. Maybe at the top in some sort of stats table
        loan_years = st.number_input("Loan Length (Years)", value=30, step=5)
        # Mortgage rate — this is the initial rate, used for all of fixed and at least the first year of  (depending on variable rate inputs)
        mortgage_years = st.number_input("Mortgage Term (Years)", value=30, step=1)
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.1)
        pmi_paid_until_equity = st.number_input("PMI Paid Until What '%' Equity", value=20, step=1)
        pmi_rate = st.number_input("PMI Rate (%)", value=0.20, step=0.01)
        mortgage_type = st.radio("Mortgage Type", ["Fixed", "Variable"])

    # Show variable rate schedule only if variable mortgage selected
        if mortgage_type == "Variable":
            st.subheader("📈 Variable Rate Schedule")
            default_rate_schedule = pd.DataFrame({
                "Year": [1, 5, 10],
                "Rate (%)": [mortgage_rate, 6.5, 7.0]
            })

            edited_rate_schedule = st.data_editor(
                default_rate_schedule,
                column_config={
                    "Year": st.column_config.NumberColumn(
                        "Year", min_value=1, step=1,
                        help="Year the rate change takes effect"
                    ),
                    "Rate (%)": st.column_config.NumberColumn(
                        "Rate (%)", min_value=0.0, step=0.1,
                        help="Interest rate for this year and onward until next change"
                    )
                },
                width="stretch",
                hide_index=True,
                num_rows="dynamic"
            )

        # Property Taxes
        st.subheader("Taxes")
        annual_property_tax = st.number_input("Annual Property Tax ($)", value=3500, step=100)
        annual_property_tax_increase = st.number_input("Annual Property Tax Increase (%)", value=3.0, step=0.1)
        state_property_transfer_tax = st.number_input("State Property Transfer Tax (%)", value=1.5, step=0.1)

    # ---------------- Extra Principal Payments ----------------
    with st.expander("💰 Extra Principal Payments"):
        st.caption("Specify any additional principal payments to accelerate payoff.")

        st.markdown("""
        **Notes on Frequency:**
        - **One-time:** Payment occurs **once** in Start Year/Month.  
        - **Monthly/Quarterly/Annually:** Payment repeats from Start to End period.  
        - **Every X Years:** Payment occurs once every X years between Start and End.
        """)

        default_payments = pd.DataFrame({
            "Amount ($)": [200, 10000],
            "Frequency": ["Monthly", "One-time"],
            "Start Year": [2025, 2030],
            "Start Month": [1, 6],
            "End Year": [2030, 2030],
            "End Month": [12, 6],
            "Interval (X Years)": [None, None]
        })

        frequency_options = ["One-time", "Monthly", "Quarterly", "Annually", "Every X Years"]
        month_options = list(range(1, 13))
        year_options = list(range(2025, 2101))

        edited_payments = st.data_editor(
            default_payments,
            column_config={
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100),
                "Frequency": st.column_config.SelectboxColumn("Frequency", options=frequency_options),
                "Start Year": st.column_config.SelectboxColumn("Start Year", options=year_options),
                "Start Month": st.column_config.SelectboxColumn("Start Month", options=month_options),
                "End Year": st.column_config.SelectboxColumn("End Year", options=year_options),
                "End Month": st.column_config.SelectboxColumn("End Month", options=month_options),
                "Interval (X Years)": st.column_config.NumberColumn("Interval (X Years)", min_value=1, step=1)
            },
            width="stretch",
            hide_index=True,
            num_rows="dynamic"
        )

    # ---------------- Routine Housing Expenses ----------------
    with st.expander("🔧 Routine Property-Related Expenses"):
        default_property_expenses = pd.DataFrame({
            "Category": ["Routine Maintenance", "Property Taxes", "Home Insurance"],
            "Amount ($)": [6000.00, 8000.00, 1100.00]
        })

        edited_property_expenses = st.data_editor(
            default_property_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category"),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100)
            },
            width="stretch",
            hide_index=True,
            num_rows="dynamic"
        )

    # ---------------- One-Time Housing Expenses ----------------
    with st.expander("⚡ One-Time Emergency Expenses"):
        default_emergency_expenses = pd.DataFrame({
            "Category": ["Appliance Replacement", "Septic Repair", "Roof Repair"],
            "Amount ($)": [1500.00, 8000.00, 12000.00],
            "Year": [2026, 2028, 2030],
            "Month": [5, 7, 9]
        })

        edited_emergency_expenses = st.data_editor(
            default_emergency_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category"),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100),
                "Year": st.column_config.SelectboxColumn("Year", options=list(range(2025, 2101))),
                "Month": st.column_config.SelectboxColumn("Month", options=list(range(1, 13)))
            },
            width="stretch",
            hide_index=True,
            num_rows="dynamic"
        )

    # ---------------- Appreciation ----------------
    with st.expander("📈 Appreciation"):
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=3.5, step=0.1)
        annual_maintenance_increase = st.number_input("Annual Maintenance Increase (%)", value=3.0, step=0.1)
        annual_insurance_increase = st.number_input("Annual Insurance Increase (%)", value=3.0, step=0.1)

    # ---------------- Rental Assumptions ----------------
    with st.expander("🏢 Rental Assumptions"):
        cost_of_rent = st.number_input("Cost of Rental Y0 ($)", value=3000, step=50)
        annual_rent_increase = st.number_input("Annual Rent Increase (%)", value=4.0, step=0.1)

    # ---------------- Investments ----------------
    with st.expander("💹 Investment (Brokerage Account)"):
        annual_stock_return = st.number_input("Annual Average Stock Market Return (%)", value=8.0, step=0.1)
        initial_tax_brokerage_balance = st.number_input("Initial Taxable Brokerage Balance ($)", value=250000, step=10000)

    # ---------------- Monte Carlo ----------------
    with st.expander("🎲 Monte Carlo Inputs"):
        mc_simulation_stock_mean = st.number_input("Simulation Stock Market Return Mean (%)", value=8.0, step=0.1)
        mc_simulation_stock_std = st.number_input("Simulation Stock Market Return Std. Dev. (%)", value=15.0, step=0.1)

# ------------------- Generate monthly and annualized mortgage ammortization tables for fixed & variable rate mortgages ----------------------

def expand_extra_payments(df, start_year, total_years):
    extra_schedule = {}
    for _, row in df.iterrows():
        amount = row["Amount ($)"]
        freq = row["Frequency"]
        sy, sm = row["Start Year"], row["Start Month"]
        ey, em = row["End Year"], row["End Month"]

        if freq == "One-time":
            extra_schedule[(sy, sm)] = extra_schedule.get((sy, sm), 0) + amount

        elif freq == "Monthly":
            for y in range(sy, ey + 1):
                for m in range(1, 13):
                    if (y > ey) or (y == ey and m > em): break
                    if (y > sy) or (y == sy and m >= sm):
                        extra_schedule[(y, m)] = extra_schedule.get((y, m), 0) + amount

        elif freq == "Quarterly":
            for y in range(sy, ey + 1):
                for m in [1, 4, 7, 10]:
                    if (y > ey) or (y == ey and m > em): break
                    if (y > sy) or (y == sy and m >= sm):
                        extra_schedule[(y, m)] = extra_schedule.get((y, m), 0) + amount

        elif freq == "Annually":
            for y in range(sy, ey + 1):
                if (y > ey): break
                if (y > sy) or (y == sy and sm >= sm):
                    extra_schedule[(y, sm)] = extra_schedule.get((y, sm), 0) + amount

        elif freq == "Every X Years":
            interval = int(row["Interval (X Years)"])
            for y in range(sy, ey + 1, interval):
                extra_schedule[(y, sm)] = extra_schedule.get((y, sm), 0) + amount

    return extra_schedule

extra_schedule = expand_extra_payments(edited_payments, purchase_year, loan_years)

def amortization_schedule(
    loan_amount,
    loan_years,
    mortgage_type="Fixed",
    mortgage_rate=0.05,
    rate_changes=None,
    extra_schedule=None,
    start_year=2025
):
    """
    Generate amortization schedule with support for fixed/variable rates
    and extra principal payments.

    Args:
        loan_amount (float): Loan principal
        loan_years (int): Loan term in years
        mortgage_type (str): "Fixed" or "Variable"
        mortgage_rate (float): Starting annual interest rate (decimal)
        rate_changes (dict): {(year, month): new_rate}, for variable loans
        extra_schedule (dict): {(year, month): extra_payment}
        start_year (int): Loan start year

    Returns:
        df_monthly (DataFrame), df_annual (DataFrame)
    """

    total_months = loan_years * 12
    balance = loan_amount
    schedule = []

    # Ensure dicts exist
    rate_changes = rate_changes or {}
    extra_schedule = extra_schedule or {}

    # Initial monthly rate + payment
    current_rate = mortgage_rate
    monthly_rate = current_rate / 12
    monthly_payment = npf.pmt(monthly_rate, total_months, -loan_amount)

    for n in range(1, total_months + 1):
        year = start_year + (n - 1) // 12
        month = ((n - 1) % 12) + 1

        # --- Apply rate change if variable mortgage ---
        if mortgage_type == "Variable" and (year, month) in rate_changes:
            current_rate = rate_changes[(year, month)]
            monthly_rate = current_rate / 12
            remaining_months = total_months - n + 1
            monthly_payment = npf.pmt(monthly_rate, remaining_months, -balance)

        # --- Interest & Principal ---
        interest = balance * monthly_rate
        principal = monthly_payment - interest

        # --- Extra Principal ---
        extra_principal = extra_schedule.get((year, month), 0.0)
        total_principal = principal + extra_principal

        balance -= total_principal
        if balance < 0:  # adjust final payment if overshoot
            total_principal += balance
            balance = 0

        schedule.append({
            "Year": year,
            "Month": month,
            "Payment": monthly_payment + extra_principal,
            "Principal": total_principal,
            "Interest": interest,
            "Extra Principal": extra_principal,
            "Balance": balance
        })

        if balance <= 0:
            break

    # --- Build DataFrames ---
    df_monthly = pd.DataFrame(schedule)

    # Aggregate to annual
    df_annual = (
        df_monthly.groupby("Year")
        .agg({
            "Payment": "sum",
            "Principal": "sum",
            "Interest": "sum",
            "Extra Principal": "sum",
            "Balance": "last"
        })
        .reset_index()
    )

    return df_monthly, df_annual

# --------------------------- MAIN FUNCTION -------------------------------------

if mortgage_type == "Fixed":
    mortgage_rate = st.number_input("Annual Interest Rate (%)", value=6.0) / 100
    df_monthly, df_annual = amortization_schedule(
    loan_amount,
    loan_years,
    "Fixed",
    mortgage_rate=mortgage_rate,
    extra_schedule=extra_schedule,
    start_year=purchase_year
)

else:  # Variable
    initial_rate = st.number_input("Initial Rate (%)", value=5.0) / 100
    adjustments = [
        (5, 0.06),  # Year 5 → 6%
        (7, 0.065)  # Year 7 → 6.5%
    ]
    # Convert to dictionary keyed by (year, month)
    rate_changes = {(purchase_year + year - 1, 1): rate for year, rate in adjustments}
    df_monthly, df_annual = amortization_schedule(
        loan_amount,
        loan_years,
        "Variable",
        mortgage_rate=initial_rate,
        rate_changes=rate_changes,
        extra_schedule=extra_schedule,
        start_year=purchase_year
    )
    
tab1, tab2 = st.tabs(["Annual", "Monthly"])
with tab1: st.dataframe(df_annual)
with tab2: st.dataframe(df_monthly)
