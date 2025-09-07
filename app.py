import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import uuid

# Custom CSS for styling
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        font-size: 14px !important;
    }
    .dataframe td, .dataframe th {
        font-size: 12px !important;
    }
    .st-container {
        padding: 10px;
        border-radius: 5px;
    }
    .stSlider > div > div > div > div {
        background-color: #e6f3ff;
        border-radius: 5px;
        padding: 10px;
    }
    .st-expander {
        background-color: #f5f5f5;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .highlight-box {
        background-color: #e6f3ff;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #d3e3ff;
    }
</style>
""", unsafe_allow_html=True)

# Page Config
st.set_page_config(page_title="Rent vs. Buy Decision Support Framework", layout="wide")
st.title("Rent vs. Buy Decision Support Framework")

# Instructions
with st.expander("Welcome & Instructions", expanded=True):
    st.markdown("""
    This tool helps you compare **renting vs. buying** a home by analyzing costs, asset growth, and key financial metrics.

    **Key Outputs:**
    - **Mortgage Metrics**: Payment details, interest, PMI, and payoff timelines.
    - **Amortization Schedule**: Detailed breakdown of payments, with refinance and extra payment impacts.
    - **Asset Metrics**: Home equity, investments, and net asset value for both scenarios.
    - **Cost Metrics**: Comprehensive cost comparisons, including one-time and repeating costs.
    - **Visualizations**: Interactive charts (line, treemap, bar) to explore trade-offs (hover for details).

    **How to Use:**
    1. Input purchase, loan, rental, and investment parameters below.
    2. Select an evaluation year to view detailed metrics and breakdowns.
    3. Explore visualizations and tables for insights.
    4. Expand sections for detailed data.

    **Methodology:**
    - Payments: Monthly (12/year) or Biweekly (26/year).
    - Costs: Buying includes P&I, PMI, taxes, insurance, maintenance, HOA, closing/points. Renting includes rent, insurance, deposits, utilities, fees.
    - Assets: Buying includes home equity and investments; renting includes investments from cost savings and down payment.
    - Investments: Cost differences invested in VTI (default 7% return).
    - Security Deposit: Treated as an opportunity cost (invested) in renting, returned at lease end.
    """)

# Inputs
st.header("Inputs")
st.markdown("Configure the parameters below to compare renting vs. buying. All fields are required unless marked optional. Use the preset options or reset to defaults for quick setup.")

# Preset and Reset Buttons
col_preset, col_reset = st.columns([1, 1])
with col_preset:
    preset = st.selectbox("Load Preset Values", ["Default", "High-Cost Urban", "Low-Cost Suburban"], help="Select a preset to auto-fill values based on common scenarios.")
with col_reset:
    if st.button("Apply", help="Revert all inputs to their default values."):
        st.session_state.clear()

# Apply presets
if preset == "High-Cost Urban":
    default_values = {
        "purchase_price": 800_000, "down_payment": 160_000, "closing_costs": 10_000, "loan_years": 30, "mortgage_rate": 4.5,
        "pmi_rate": 0.25, "pmi_equity_threshold": 20, "property_taxes": 12_000, "home_insurance": 1500, "maintenance": 8000,
        "hoa_fees": 2400, "cost_of_rent": 4000, "renters_insurance": 400, "security_deposit": 4000, "rental_utilities": 3000,
        "pet_fee": 600, "application_fee": 75, "lease_renewal_fee": 150, "parking_fee": 100, "vti_annual_return": 7.0,
        "annual_appreciation": 3.5, "annual_maintenance_increase": 3.5, "annual_insurance_increase": 3.5, "annual_hoa_increase": 3.5,
        "annual_rent_increase": 4.0
    }
elif preset == "Low-Cost Suburban":
    default_values = {
        "purchase_price": 300_000, "down_payment": 60_000, "closing_costs": 3000, "loan_years": 15, "mortgage_rate": 5.5,
        "pmi_rate": 0.15, "pmi_equity_threshold": 20, "property_taxes": 5000, "home_insurance": 800, "maintenance": 4000,
        "hoa_fees": 600, "cost_of_rent": 1800, "renters_insurance": 200, "security_deposit": 1800, "rental_utilities": 1800,
        "pet_fee": 300, "application_fee": 40, "lease_renewal_fee": 50, "parking_fee": 25, "vti_annual_return": 6.5,
        "annual_appreciation": 2.5, "annual_maintenance_increase": 2.5, "annual_insurance_increase": 2.5, "annual_hoa_increase": 2.5,
        "annual_rent_increase": 2.0
    }
else:
    default_values = {
        "purchase_price": 500_000, "down_payment": 100_000, "closing_costs": 5000, "loan_years": 30, "mortgage_rate": 5.0,
        "pmi_rate": 0.20, "pmi_equity_threshold": 20, "property_taxes": 8000, "home_insurance": 1100, "maintenance": 6000,
        "hoa_fees": 1200, "cost_of_rent": 3000, "renters_insurance": 300, "security_deposit": 3000, "rental_utilities": 2400,
        "pet_fee": 500, "application_fee": 50, "lease_renewal_fee": 100, "parking_fee": 50, "vti_annual_return": 7.0,
        "annual_appreciation": 3.0, "annual_maintenance_increase": 3.0, "annual_insurance_increase": 3.0, "annual_hoa_increase": 3.0,
        "annual_rent_increase": 3.0
    }

# Initialize session state for inputs
for key, value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Buying Parameters
st.subheader("Buying Parameters")
with st.container(border=True):
    st.markdown("### Purchase and Loan Details")
    col1, col2 = st.columns(2)
    with col1:
        purchase_year = st.number_input("Purchase Year", value=2025, step=1, min_value=2000, max_value=2100, help="Year you plan to purchase the home.")
        purchase_price = st.number_input("Purchase Price ($)", value=st.session_state["purchase_price"], step=10_000, min_value=0, help="Total cost of the home.")
        down_payment = st.number_input("Down Payment ($)", value=st.session_state["down_payment"], step=1_000, min_value=0, max_value=purchase_price, help="Initial payment toward purchase price.")
        if down_payment > purchase_price:
            st.warning("Down payment cannot exceed purchase price.")
        closing_costs = st.number_input("Closing Costs ($)", value=st.session_state["closing_costs"], step=500, min_value=0, help="One-time costs at purchase (e.g., fees, title).")
        closing_costs_method = st.selectbox("Closing Costs Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance closing costs or pay upfront.")
        loan_amount = purchase_price - down_payment + (closing_costs if closing_costs_method == "Add to Loan Balance" else 0)
        percent_down = (down_payment / purchase_price * 100) if purchase_price > 0 else 0
        st.metric("Calculated Loan Amount", f"${loan_amount:,.0f}")
        st.metric("Down Payment Percentage", f"{percent_down:.2f}%")

    with col2:
        loan_years = st.number_input("Loan Length (Years)", value=st.session_state["loan_years"], step=1, min_value=1, max_value=50, help="Duration of the mortgage.")
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=st.session_state["mortgage_rate"], step=0.01, min_value=0.0, format="%.3f", help="Annual interest rate for the mortgage.")
        pmi_rate = st.number_input("PMI Rate (%)", value=st.session_state["pmi_rate"], step=0.01, min_value=0.0, help="Private Mortgage Insurance rate, applied if equity < threshold.")
        pmi_equity_threshold = st.number_input("PMI Paid Until Equity (%)", value=st.session_state["pmi_equity_threshold"], step=1, min_value=0, max_value=100, help="Equity percentage at which PMI stops.")
        payment_frequency = st.selectbox("Payment Frequency", ["Monthly", "Biweekly"], index=0, help="Monthly (12/year) or biweekly (26/year) payments.")
        mortgage_type = st.selectbox("Mortgage Type", ["Fixed", "Variable"], index=0, help="Fixed or variable rate mortgage.")

        buy_points = st.checkbox("Buy Points to Reduce Rate?", value=False, help="Pay points to lower mortgage rate.")
        points = 0
        discount_per_point = 0.25
        points_cost_method = "Add to Loan Balance"
        points_cost = 0
        effective_rate = mortgage_rate
        if buy_points:
            points = st.number_input("Number of Points", value=1.0, step=0.25, min_value=0.0, help="Points purchased (1 point = 1% of loan amount).")
            discount_per_point = st.number_input("Rate Discount per Point (%)", value=0.25, step=0.01, min_value=0.0, help="Rate reduction per point purchased.")
            points_cost_method = st.selectbox("Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance or pay points upfront.")
            effective_rate = mortgage_rate - (discount_per_point * points)
            points_cost = points * (purchase_price - down_payment) * 0.01
            if buy_points:
                st.metric("Effective Rate After Points", f"{effective_rate:.3f}%")
                st.metric("Points Cost", f"${points_cost:,.0f}")

    if mortgage_type == "Variable":
        st.markdown("### Variable Rate Schedule")
        default_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [mortgage_rate, mortgage_rate + 1.5, mortgage_rate + 2.0]})
        rate_schedule = st.data_editor(
            default_schedule,
            column_config={
                "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=loan_years, step=1, help="Year the rate applies."),
                "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1, help="Mortgage rate for the specified year.")
            },
            hide_index=True,
            num_rows="dynamic"
        )
    else:
        rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]})

# Ongoing Expenses
st.subheader("Ongoing Homeownership Expenses")
with st.container(border=True):
    st.markdown("### Regular and Emergency Expenses")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Regular Expenses**")
        st.markdown("Enter annual recurring expenses for homeownership.")
        default_property_expenses = pd.DataFrame({
            "Category": ["Property Taxes", "Home Insurance", "Routine Maintenance", "HOA Fees"],
            "Amount ($)": [st.session_state["property_taxes"], st.session_state["home_insurance"], st.session_state["maintenance"], st.session_state["hoa_fees"]]
        })
        edited_property_expenses = st.data_editor(
            default_property_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category", help="Type of recurring expense."),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100, help="Annual cost in dollars.")
            },
            hide_index=True,
            num_rows="dynamic"
        )

    with col2:
        st.markdown("**Emergency Expenses**")
        st.markdown("Enter one-time emergency repair costs.")
        default_emergency_expenses = pd.DataFrame({
            "Category": ["Appliance Replacement", "Septic Repair", "Roof Repair"],
            "Amount ($)": [1500, 8000, 12000],
            "Year": [purchase_year + 1, purchase_year + 5, purchase_year + 10],
            "Month": [5, 7, 9]
        })
        edited_emergency_expenses = st.data_editor(
            default_emergency_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category", help="Type of emergency repair."),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100, help="Cost of the repair."),
                "Year": st.column_config.NumberColumn("Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1, help="Year of the repair."),
                "Month": st.column_config.NumberColumn("Month", min_value=1, max_value=12, step=1, help="Month of the repair.")
            },
            hide_index=True,
            num_rows="dynamic"
        )

    st.markdown("### Appreciation and Growth Rates")
    col1, col2 = st.columns(2)
    with col1:
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=st.session_state["annual_appreciation"], step=0.1, min_value=0.0, help="Expected annual increase in home value.")
        annual_maintenance_increase = st.number_input("Annual Maintenance Increase (%)", value=st.session_state["annual_maintenance_increase"], step=0.1, min_value=0.0, help="Annual increase in maintenance costs.")
    with col2:
        annual_insurance_increase = st.number_input("Annual Insurance Increase (%)", value=st.session_state["annual_insurance_increase"], step=0.1, min_value=0.0, help="Annual increase in home insurance costs.")
        annual_hoa_increase = st.number_input("Annual HOA Increase (%)", value=st.session_state["annual_hoa_increase"], step=0.1, min_value=0.0, help="Annual increase in HOA fees.")

# Rental Parameters
st.subheader("Rental Parameters")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        cost_of_rent = st.number_input("Initial Monthly Rent ($)", value=st.session_state["cost_of_rent"], step=50, min_value=0, help="Monthly rent excluding utilities and fees.")
        annual_rent_increase = st.number_input("Annual Rent Increase (%)", value=st.session_state["annual_rent_increase"], step=0.1, min_value=0.0, help="Expected annual increase in rent.")
        renters_insurance = st.number_input("Annual Renters' Insurance ($)", value=st.session_state["renters_insurance"], step=50, min_value=0, help="Yearly cost of renters' insurance.")
        security_deposit = st.number_input("Security Deposit ($)", value=st.session_state["security_deposit"], step=100, min_value=0, help="One-time deposit, invested as opportunity cost.")
    with col2:
        rental_utilities = st.number_input("Annual Rental Utilities ($)", value=st.session_state["rental_utilities"], step=100, min_value=0, help="Yearly utility costs for renting.")
        pet_fee = st.number_input("Pet Fee/Deposit ($)", value=st.session_state["pet_fee"], step=50, min_value=0, help="One-time or annual pet fee, depending on frequency.")
        pet_fee_frequency = st.selectbox("Pet Fee Frequency", ["One-time", "Annual"], index=0, help="Whether pet fee is one-time or annual.")
        application_fee = st.number_input("Application Fee ($)", value=st.session_state["application_fee"], step=10, min_value=0, help="One-time fee per lease application.")
        lease_renewal_fee = st.number_input("Annual Lease Renewal Fee ($)", value=st.session_state["lease_renewal_fee"], step=50, min_value=0, help="Annual fee for renewing lease.")
        parking_fee = st.number_input("Monthly Parking Fee ($)", value=st.session_state["parking_fee"], step=10, min_value=0, help="Monthly parking cost.")

# Advanced Options
st.subheader("Advanced Options")
with st.expander("Refinance and Extra Payments", expanded=False):
    st.markdown("### Refinance Options")
    show_refinance = st.checkbox("Model a Refinance?", value=False, help="Include a refinance scenario in calculations.")
    refi_rate = None
    refi_term_years = None
    refi_start_date = None
    refi_costs = None
    roll_costs = None
    refi_payment_frequency = None
    refi_mortgage_type = None
    refi_rate_schedule = None
    refi_periods_per_year = None
    refi_buy_points = False
    refi_points = 0
    refi_discount_per_point = 0.25
    refi_points_cost_method = "Add to Loan Balance"
    refi_points_cost = 0
    refi_effective_rate = None

    if show_refinance:
        col1, col2 = st.columns(2)
        with col1:
            refi_rate = st.number_input("Refinance Rate (%)", value=4.0, step=0.01, min_value=0.0, format="%.3f", help="Interest rate for refinanced loan.")
            refi_term_years = st.number_input("Refinance Term (Years)", value=20, step=1, min_value=1, max_value=50, help="Duration of refinanced loan.")
            refi_start_date = st.date_input("Refinance Start Date", min_value=datetime(purchase_year, 1, 1), max_value=datetime(purchase_year + loan_years, 12, 31), help="Date refinance begins.")
        with col2:
            refi_costs = st.number_input("Refinance Closing Costs ($)", value=3000, step=500, min_value=0, help="One-time costs for refinancing.")
            roll_costs = st.selectbox("Refinance Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance or pay refinance costs upfront.")
            refi_payment_frequency = st.selectbox("Refinance Payment Frequency", ["Monthly", "Biweekly"], index=0, help="Payment frequency for refinanced loan.")
            refi_mortgage_type = st.selectbox("Refinance Mortgage Type", ["Fixed", "Variable"], index=0, help="Fixed or variable rate for refinanced loan.")
            refi_periods_per_year = 12 if refi_payment_frequency == "Monthly" else 26
            refi_effective_rate = refi_rate

        refi_buy_points = st.checkbox("Buy Points for Refinance?", value=False, help="Pay points to lower refinance rate.")
        if refi_buy_points:
            col1, col2 = st.columns(2)
            with col1:
                refi_points = st.number_input("Refinance Points", value=1.0, step=0.25, min_value=0.0, help="Points purchased for refinance.")
                refi_discount_per_point = st.number_input("Refinance Rate Discount per Point (%)", value=0.25, step=0.01, min_value=0.0, help="Rate reduction per refinance point.")
            with col2:
                refi_points_cost_method = st.selectbox("Refinance Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance or pay refinance points upfront.")
                refi_effective_rate = refi_rate - (refi_discount_per_point * refi_points)
                refi_points_cost = refi_points * (purchase_price - down_payment) * 0.01
                st.metric("Refinance Effective Rate", f"{refi_effective_rate:.3f}%")
                st.metric("Refinance Points Cost", f"${refi_points_cost:,.0f}")

        if refi_mortgage_type == "Variable":
            st.markdown("### Refinance Variable Rate Schedule")
            default_refi_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [refi_effective_rate, refi_effective_rate + 1.5, refi_effective_rate + 2.0]})
            refi_rate_schedule = st.data_editor(
                default_refi_schedule,
                column_config={
                    "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=refi_term_years, step=1, help="Year the refinance rate applies."),
                    "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1, help="Refinance rate for the specified year.")
                },
                hide_index=True,
                num_rows="dynamic"
            )
        else:
            refi_rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [refi_effective_rate]})

# Inside the "Advanced Options" section, replace the Extra Principal Payments part
st.markdown("### Extra Principal Payments")
st.markdown("Add extra payments to reduce your mortgage principal faster. Ensure all required fields are filled to avoid errors.")
default_payments = pd.DataFrame({
    "Amount ($)": [200, 10000],
    "Frequency": ["Monthly", "One-time"],
    "Start Year": [purchase_year, purchase_year + 5],
    "Start Month": [1, 6],
    "End Year": [purchase_year + 5, purchase_year + 5],
    "End Month": [12, 6],
    "Interval (Years)": [None, None]
})
extra_payments = st.data_editor(
    default_payments,
    column_config={
        "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100, help="Amount of extra payment.", required=True),
        "Frequency": st.column_config.SelectboxColumn("Frequency", options=["One-time", "Monthly", "Quarterly", "Annually", "Every X Years"], help="How often the payment is made.", required=True),
        "Start Year": st.column_config.NumberColumn("Start Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1, help="Year payments start.", required=True),
        "Start Month": st.column_config.NumberColumn("Start Month", min_value=1, max_value=12, step=1, help="Month payments start.", required=True),
        "End Year": st.column_config.NumberColumn("End Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1, help="Year payments end.", required=True),
        "End Month": st.column_config.NumberColumn("End Month", min_value=1, max_value=12, step=1, help="Month payments end.", required=True),
        "Interval (Years)": st.column_config.NumberColumn("Interval (Years)", min_value=1, step=1, help="Interval for 'Every X Years' payments (optional).")
    },
    hide_index=True,
    num_rows="dynamic"
)

# Validate extra_payments DataFrame
required_columns = ["Amount ($)", "Frequency", "Start Year", "Start Month", "End Year", "End Month"]
invalid_rows = extra_payments[required_columns].isna().any(axis=1)
if invalid_rows.any():
    st.warning("Some extra payment rows have missing values in required fields (Amount, Frequency, Start/End Year/Month). These rows will be ignored.")
    extra_payments = extra_payments[~invalid_rows].copy()

# Additional validation for Interval (Years)
if "Interval (Years)" in extra_payments.columns:
    extra_payments.loc[
        (extra_payments["Frequency"] != "Every X Years") | extra_payments["Interval (Years)"].isna(),
        "Interval (Years)"
    ] = None

# Investment and Evaluation Period
st.subheader("Investment and Analysis Period")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Investment Returns")
        vti_annual_return = st.number_input("Annual VTI Return (%)", value=st.session_state["vti_annual_return"], step=0.1, min_value=0.0, help="Expected annual return on investments (e.g., VTI).")
    with col2:
        st.markdown("### Evaluation Period")
        eval_start_year = st.number_input("Evaluation Start Year", value=2025, step=1, min_value=2000, max_value=2100, help="Start year for analysis.")
        eval_end_year = st.number_input("Evaluation End Year", value=2070, step=1, min_value=eval_start_year, max_value=2100, help="End year for analysis.")
        if eval_end_year < eval_start_year:
            st.warning("End year must be greater than or equal to start year.")

# Functions
@st.cache_data
def expand_extra_payments(df, start_year, loan_years, frequency):
    extra_schedule = {}
    start_date = datetime(start_year, 1, 1)
    periods_per_year = 12 if frequency == "Monthly" else 26
    n_payments = loan_years * periods_per_year
    delta = pd.DateOffset(months=1) if frequency == "Monthly" else timedelta(days=14)
    payment_dates = [start_date + i * delta for i in range(n_payments)]

    # Filter out rows with any NaN in required columns
    required_columns = ["Amount ($)", "Frequency", "Start Year", "Start Month", "End Year", "End Month"]
    df = df.dropna(subset=required_columns, how="any").copy()

    for _, row in df.iterrows():
        try:
            amt = float(row["Amount ($)"])
            freq = row["Frequency"]
            start_y = int(row["Start Year"])
            start_m = int(row["Start Month"])
            end_y = int(row["End Year"])
            end_m = int(row["End Month"])
            interval = int(row["Interval (Years)"]) if not pd.isna(row["Interval (Years)"]) and freq == "Every X Years" else 1

            # Validate inputs
            if amt <= 0 or start_y < start_year or start_y > start_year + loan_years or start_m < 1 or start_m > 12 or end_y < start_y or end_y > start_year + loan_years or end_m < 1 or end_m > 12:
                continue  # Skip invalid rows

            extra_dates = []
            if freq == "One-time":
                extra_dates.append(datetime(start_y, start_m, 1))
            else:
                current = datetime(start_y, start_m, 1)
                end = datetime(end_y, end_m, 28)
                while current <= end:
                    extra_dates.append(current)
                    if freq == "Monthly":
                        current += pd.DateOffset(months=1)
                    elif freq == "Quarterly":
                        current += pd.DateOffset(months=3)
                    elif freq == "Annually":
                        current += pd.DateOffset(years=1)
                    elif freq == "Every X Years":
                        current += pd.DateOffset(years=interval)

            for apply_date in extra_dates:
                matching_dates = [pdate for pdate in payment_dates if pdate.year == apply_date.year and pdate.month == apply_date.month]
                if matching_dates:
                    if freq == "Monthly" and frequency == "Biweekly" and len(matching_dates) > 1:
                        split_amt = amt / len(matching_dates)
                        for pdate in matching_dates:
                            extra_schedule[pdate] = extra_schedule.get(pdate, 0) + split_amt
                    else:
                        apply_pdate = min(matching_dates, key=lambda x: abs((x - apply_date).days))
                        extra_schedule[apply_pdate] = extra_schedule.get(apply_pdate, 0) + amt
        except (ValueError, TypeError):
            continue  # Skip rows with invalid data (e.g., non-numeric values)

    return extra_schedule

@st.cache_data
def amortization_schedule(
    principal,
    years,
    periods_per_year=12,
    start_date="2025-01-01",
    extra_schedule=None,
    rate_schedule=None,
    mortgage_type="Fixed",
    purchase_year=2025,
    mortgage_rate=5.0,
    pmi_rate=0.0,
    pmi_equity_threshold=20.0,
    purchase_price=500_000,
    refi_start_date=None,
    refi_principal=None,
    refi_years=None,
    refi_periods_per_year=None,
    refi_rate_schedule=None,
    refi_mortgage_type="Fixed",
    refi_mortgage_rate=None
):
    balance = principal
    start_date = pd.to_datetime(start_date)
    refi_start_date = pd.to_datetime(refi_start_date) if refi_start_date else None
    extra_schedule = extra_schedule or {}
    schedule = []

    if mortgage_type == "Fixed":
        rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]})
    elif rate_schedule is None or rate_schedule.empty:
        rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]})
    else:
        if not any(rate_schedule["Year"] == 1):
            rate_schedule = pd.concat([
                pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]}),
                rate_schedule
            ]).sort_values("Year").reset_index(drop=True)

    if refi_mortgage_type == "Fixed" and refi_mortgage_rate is not None:
        refi_rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [refi_mortgage_rate]})
    elif refi_rate_schedule is None or refi_rate_schedule.empty:
        refi_rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [refi_mortgage_rate]}) if refi_mortgage_rate else rate_schedule
    else:
        if not any(refi_rate_schedule["Year"] == 1):
            refi_rate_schedule = pd.concat([
                pd.DataFrame({"Year": [1], "Rate (%)": [refi_mortgage_rate if refi_mortgage_rate else mortgage_rate]}),
                refi_rate_schedule
            ]).sort_values("Year").reset_index(drop=True)

    n_periods = years * periods_per_year
    if refi_start_date and refi_years and refi_periods_per_year:
        refi_start_period = int(((refi_start_date - start_date).days / 365.25) * periods_per_year)
        n_periods = max(n_periods, refi_start_period + refi_years * refi_periods_per_year)

    delta = pd.DateOffset(months=1) if periods_per_year == 12 else timedelta(days=14)
    refi_delta = pd.DateOffset(months=1) if refi_periods_per_year == 12 else timedelta(days=14) if refi_periods_per_year else delta

    year_elapsed = max(1, start_date.year - purchase_year + 1)
    applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
    current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else mortgage_rate / 100
    monthly_payment = npf.pmt(current_rate / 12, years * 12, -principal)
    payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

    is_refinanced = False
    refi_start_period = 0
    for n in range(n_periods):
        current_date = start_date + (n * delta) if not is_refinanced else refi_start_date + (n - refi_start_period) * refi_delta
        year_elapsed = max(1, current_date.year - purchase_year + 1)

        if refi_start_date and current_date >= refi_start_date and not is_refinanced:
            is_refinanced = True
            balance = refi_principal
            periods_per_year = refi_periods_per_year
            rate_schedule = refi_rate_schedule
            mortgage_type = refi_mortgage_type
            purchase_year = refi_start_date.year
            refi_start_period = n
            year_elapsed = 1
            applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
            current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else refi_mortgage_rate / 100 if refi_mortgage_rate else mortgage_rate / 100
            monthly_payment = npf.pmt(current_rate / 12, refi_years * 12, -refi_principal)
            payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

        applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
        current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else (refi_mortgage_rate / 100 if is_refinanced and refi_mortgage_rate else mortgage_rate / 100)

        if mortgage_type == "Variable" and n > 0:
            remaining_periods = (years if not is_refinanced else refi_years) * periods_per_year - n
            monthly_payment = npf.pmt(current_rate / 12, remaining_periods / (periods_per_year / 12), -balance)
            payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

        equity = (purchase_price - balance) / purchase_price * 100 if purchase_price > 0 else 0
        pmi_payment = round((principal * pmi_rate / 100 / 12), 2) if equity < pmi_equity_threshold else 0

        extra = 0
        if extra_schedule:
            closest_date = min(extra_schedule.keys(), key=lambda x: abs((x - current_date).days), default=None)
            if closest_date and abs((closest_date - current_date).days) <= (30 if periods_per_year == 12 else 14):
                extra = extra_schedule.get(closest_date, 0)

        interest = round(balance * (current_rate / periods_per_year), 2)
        principal_paid = round(payment - interest, 2)

        if principal_paid + extra > balance:
            principal_paid = round(balance - extra, 2)
            payment = round(principal_paid + interest, 2)

        balance = round(balance - (principal_paid + extra), 2)

        schedule.append({
            "Date": current_date,
            "Payment": payment,
            "Interest": interest,
            "Principal": principal_paid,
            "Extra Principal Payments": extra,
            "PMI": pmi_payment,
            "Balance": balance,
            "Loan Type": "Refinance" if is_refinanced else "Original",
            "Effective Rate (%)": round(current_rate * 100, 2)
        })

        if balance <= 0:
            break

    df = pd.DataFrame(schedule)
    df_monthly = df.groupby(df["Date"].dt.to_period("M")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra Principal Payments": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Loan Type": "last",
        "Effective Rate (%)": "last"
    }).reset_index()
    df_monthly["Date"] = df_monthly["Date"].dt.to_timestamp()

    df_annual = df.groupby(df["Date"].dt.to_period("Y")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra Principal Payments": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Loan Type": "last",
        "Effective Rate (%)": "last"
    }).reset_index()
    df_annual["Date"] = df_annual["Date"].dt.to_timestamp()

    return df, df_monthly, df_annual

@st.cache_data
def calculate_cost_comparison(
    annual_df,
    edited_property_expenses,
    edited_emergency_expenses,
    purchase_year,
    eval_start_year,
    eval_end_year,
    annual_appreciation,
    annual_insurance_increase,
    annual_maintenance_increase,
    annual_hoa_increase,
    cost_of_rent,
    annual_rent_increase,
    renters_insurance,
    security_deposit,
    points_cost,
    points_cost_method,
    closing_costs,
    closing_costs_method,
    refi_costs,
    roll_costs,
    refi_points_cost,
    refi_points_cost_method,
    rental_utilities,
    pet_fee,
    pet_fee_frequency,
    application_fee,
    lease_renewal_fee,
    parking_fee,
    purchase_price,
    vti_annual_return=7.0,
    down_payment=0
):
    years = range(eval_start_year, eval_end_year + 1)
    comparison_data = []
    cumulative_buy = 0
    cumulative_rent = 0
    taxes = edited_property_expenses[edited_property_expenses["Category"] == "Property Taxes"]["Amount ($)"].iloc[0] if "Property Taxes" in edited_property_expenses["Category"].values else 0
    insurance = edited_property_expenses[edited_property_expenses["Category"] == "Home Insurance"]["Amount ($)"].iloc[0] if "Home Insurance" in edited_property_expenses["Category"].values else 0
    maintenance = edited_property_expenses[edited_property_expenses["Category"] == "Routine Maintenance"]["Amount ($)"].iloc[0] if "Routine Maintenance" in edited_property_expenses["Category"].values else 0
    hoa = edited_property_expenses[edited_property_expenses["Category"] == "HOA Fees"]["Amount ($)"].iloc[0] if "HOA Fees" in edited_property_expenses["Category"].values else 0
    current_rent = cost_of_rent
    current_renters_insurance = renters_insurance
    current_deposit = security_deposit
    current_utilities = rental_utilities
    current_pet_fee = pet_fee
    current_parking = parking_fee
    home_value = purchase_price
    base_home_value = purchase_price
    buy_investment = 0
    rent_investment = down_payment + security_deposit

    for year in years:
        year_idx = year - purchase_year
        if year <= purchase_year + loan_years and year in annual_df["Date"].dt.year.values:
            p_and_i = annual_df[annual_df["Date"].dt.year == year]["Payment"].sum() + annual_df[annual_df["Date"].dt.year == year]["Extra Principal Payments"].sum()
            pmi = annual_df[annual_df["Date"].dt.year == year]["PMI"].sum()
            year_balance = annual_df[annual_df["Date"].dt.year == year]["Balance"].iloc[-1]
        else:
            p_and_i = 0
            pmi = 0
            year_balance = 0

        year_taxes = taxes * (1 + annual_appreciation / 100) ** year_idx
        year_insurance = insurance * (1 + annual_insurance_increase / 100) ** year_idx
        year_maintenance = maintenance * (1 + annual_maintenance_increase / 100) ** year_idx
        year_hoa = hoa * (1 + annual_hoa_increase / 100) ** year_idx
        year_emergency = edited_emergency_expenses[edited_emergency_expenses["Year"] == year]["Amount ($)"].sum() if not edited_emergency_expenses.empty else 0
        year_closing = (closing_costs if year == purchase_year and closing_costs_method == "Pay Upfront" else 0) + (refi_costs if show_refinance and refi_start_date and refi_start_date.year == year and roll_costs == "Pay Upfront" else 0)
        year_points = (points_cost if year == purchase_year and points_cost_method == "Pay Upfront" else 0) + (refi_points_cost if show_refinance and refi_start_date and refi_start_date.year == year and refi_points_cost_method == "Pay Upfront" else 0)
        financing_method = (
            f"{'Closing: Upfront' if year == purchase_year and closing_costs_method == 'Pay Upfront' else 'Closing: Financed' if year == purchase_year else ''}"
            f"{'; ' if year == purchase_year and points_cost_method == 'Pay Upfront' else ''}{'Points: Upfront' if year == purchase_year and points_cost_method == 'Pay Upfront' else 'Points: Financed' if year == purchase_year else ''}"
            f"{'; ' if show_refinance and refi_start_date and refi_start_date.year == year else ''}{'Refi Closing: Upfront' if show_refinance and refi_start_date and refi_start_date.year == year and roll_costs == 'Pay Upfront' else 'Refi Closing: Financed' if show_refinance and refi_start_date and refi_start_date.year == year else ''}"
            f"{'; ' if show_refinance and refi_start_date and refi_start_date.year == year and refi_points_cost_method == 'Pay Upfront' else ''}{'Refi Points: Upfront' if show_refinance and refi_start_date and refi_start_date.year == year and refi_points_cost_method == 'Pay Upfront' else 'Refi Points: Financed' if show_refinance and refi_start_date and refi_start_date.year == year else ''}"
        ).strip("; ")
        indirect_costs = pmi + year_taxes + year_insurance + year_maintenance + year_hoa + year_emergency + year_closing + year_points
        buy_cost = p_and_i + indirect_costs

        year_rent = current_rent * 12
        year_renters_insurance = current_renters_insurance
        year_deposit = current_deposit if year == purchase_year else 0
        year_utilities = current_utilities
        year_pet_fee = current_pet_fee if pet_fee_frequency == "Annual" or (pet_fee_frequency == "One-time" and year == purchase_year) else 0
        year_application_fee = application_fee if year == purchase_year else 0
        year_renewal_fee = lease_renewal_fee if year > purchase_year else 0
        year_parking = current_parking * 12
        rent_cost = year_rent + year_renters_insurance + year_deposit + year_utilities + year_pet_fee + year_application_fee + year_renewal_fee + year_parking

        cumulative_buy += buy_cost
        cumulative_rent += rent_cost
        home_value = home_value * (1 + annual_appreciation / 100)
        appreciation = home_value - base_home_value
        equity = home_value - year_balance if year_balance > 0 else home_value

        cost_difference = buy_cost - rent_cost
        if cost_difference > 0:
            rent_investment = rent_investment * (1 + vti_annual_return / 100) + cost_difference
            buy_investment = buy_investment * (1 + vti_annual_return / 100)
        else:
            buy_investment = buy_investment * (1 + vti_annual_return / 100) + abs(cost_difference)
            rent_investment = rent_investment * (1 + vti_annual_return / 100)

        buy_total_assets = equity + buy_investment
        rent_total_assets = rent_investment

        comparison_data.append({
            "Year": year,
            "Direct Costs (P&I)": p_and_i,
            "Indirect Costs": indirect_costs,
            "PMI": pmi,
            "Property Taxes": year_taxes,
            "Home Insurance": year_insurance,
            "Maintenance": year_maintenance,
            "Emergency": year_emergency,
            "HOA Fees": year_hoa,
            "Closing Costs": year_closing,
            "Points Costs": year_points,
            "Financing Method": financing_method if financing_method else "None",
            "Total Buying Cost": buy_cost,
            "Total Renting Cost": rent_cost,
            "Cumulative Buying Cost": cumulative_buy,
            "Cumulative Renting Cost": cumulative_rent,
            "Cost Difference (Buy - Rent)": cumulative_buy - cumulative_rent,
            "Equity Gain": equity,
            "Appreciation": appreciation,
            "Buying Investment": buy_investment,
            "Renting Investment": rent_investment,
            "Buying Total Assets": buy_total_assets,
            "Renting Total Assets": rent_total_assets,
            "Asset Difference (Buy - Rent)": buy_total_assets - rent_total_assets,
            "Rent": year_rent,
            "Renters Insurance": year_renters_insurance,
            "Security Deposit": year_deposit,
            "Utilities": year_utilities,
            "Pet Fees": year_pet_fee,
            "Application Fee": year_application_fee,
            "Lease Renewal Fee": year_renewal_fee,
            "Parking Fee": year_parking
        })

        current_rent *= (1 + annual_rent_increase / 100)
        current_renters_insurance *= (1 + annual_rent_increase / 100)
        current_utilities *= (1 + annual_rent_increase / 100)
        current_pet_fee *= (1 + annual_rent_increase / 100) if pet_fee_frequency == "Annual" else 1
        current_parking *= (1 + annual_rent_increase / 100)

    return pd.DataFrame(comparison_data)

@st.cache_data
def calculate_breakeven(no_refi_monthly_df, main_monthly_df, refi_costs, refi_points_cost, roll_costs, refi_points_cost_method):
    total_costs = (refi_costs if roll_costs == "Pay Upfront" else 0) + (refi_points_cost if refi_points_cost_method == "Pay Upfront" else 0)
    if total_costs == 0:
        return None, None

    no_refi_cum_interest = no_refi_monthly_df['Interest'].cumsum()
    no_refi_cum_pmi = no_refi_monthly_df['PMI'].cumsum()
    refi_cum_interest = main_monthly_df['Interest'].cumsum()
    refi_cum_pmi = main_monthly_df['PMI'].cumsum()
    savings = (no_refi_cum_interest + no_refi_cum_pmi) - (refi_cum_interest + refi_cum_pmi)

    breakeven_idx = savings[savings >= total_costs].index
    if not breakeven_idx.empty:
        breakeven_month = breakeven_idx[0] + 1
        breakeven_years = breakeven_month / 12
        return breakeven_years, breakeven_month
    return None, None

@st.cache_data
def get_remaining_balance(schedule_df, refi_date):
    refi_date = pd.to_datetime(refi_date)
    mask = schedule_df["Date"] <= refi_date
    return schedule_df.loc[mask, "Balance"].iloc[-1] if mask.any() else schedule_df["Balance"].iloc[0]

# Calculations
effective_principal = loan_amount + (points_cost if points_cost_method == "Add to Loan Balance" else 0)
effective_mortgage_rate = effective_rate

extra_schedule = expand_extra_payments(extra_payments, purchase_year, loan_years, payment_frequency)
extra_schedule_monthly = expand_extra_payments(extra_payments, purchase_year, loan_years, "Monthly")

no_refi_schedule_df, no_refi_monthly_df, no_refi_annual_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=12,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=extra_schedule_monthly,
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price
)

refi_effective_principal = None
if show_refinance:
    refi_effective_principal = get_remaining_balance(no_refi_schedule_df, refi_start_date) + (refi_costs if roll_costs == "Add to Loan Balance" else 0) + (refi_points_cost if refi_points_cost_method == "Add to Loan Balance" else 0)

main_periods_per_year = 12 if payment_frequency == "Monthly" else 26
main_schedule_df, main_monthly_df, main_annual_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=main_periods_per_year,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=extra_schedule,
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price,
    refi_start_date=refi_start_date if show_refinance else None,
    refi_principal=refi_effective_principal,
    refi_years=refi_term_years,
    refi_periods_per_year=refi_periods_per_year if show_refinance else None,
    refi_rate_schedule=refi_rate_schedule,
    refi_mortgage_type=refi_mortgage_type,
    refi_mortgage_rate=refi_effective_rate
)

no_extra_schedule_df, no_extra_monthly_df, no_extra_annual_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=main_periods_per_year,
    start_date=f"{purchase_year}-01-01",
    extra_schedule={},
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price,
    refi_start_date=refi_start_date if show_refinance else None,
    refi_principal=refi_effective_principal,
    refi_years=refi_term_years,
    refi_periods_per_year=refi_periods_per_year if show_refinance else None,
    refi_rate_schedule=refi_rate_schedule,
    refi_mortgage_type=refi_mortgage_type,
    refi_mortgage_rate=refi_effective_rate
)

monthly_payment = main_schedule_df['Payment'].iloc[0] if main_periods_per_year == 12 else main_schedule_df['Payment'].iloc[0] * 26 / 12
payment_per_period = main_schedule_df['Payment'].iloc[0]
total_interest = main_schedule_df['Interest'].sum()
total_pmi = main_schedule_df['PMI'].sum()
payoff_years = len(main_schedule_df) / main_periods_per_year
payoff_date = main_schedule_df[main_schedule_df['Balance'] <= 0]['Date'].min() if (main_schedule_df['Balance'] <= 0).any() else main_schedule_df['Date'].max()
payoff_year = payoff_date.year
payoff_month = payoff_date.month

interest_saved_refi = 0
pmi_saved_refi = 0
payoff_difference_refi = 0
breakeven_years = None
breakeven_months = None
if show_refinance and refi_start_date:
    interest_saved_refi = no_refi_schedule_df['Interest'].sum() - total_interest
    pmi_saved_refi = no_refi_schedule_df['PMI'].sum() - total_pmi
    payoff_difference_refi = len(no_refi_schedule_df) / 12 - payoff_years
    breakeven_years, breakeven_months = calculate_breakeven(no_refi_monthly_df, main_monthly_df, refi_costs, refi_points_cost, roll_costs, refi_points_cost_method)

interest_saved_biweekly = 0
payoff_difference_biweekly = 0
if payment_frequency == "Biweekly":
    monthly_comparison_df, monthly_comparison_monthly_df, monthly_comparison_annual_df = amortization_schedule(
        principal=effective_principal,
        years=loan_years,
        periods_per_year=12,
        start_date=f"{purchase_year}-01-01",
        extra_schedule=extra_schedule_monthly,
        rate_schedule=rate_schedule,
        mortgage_type=mortgage_type,
        purchase_year=purchase_year,
        mortgage_rate=effective_mortgage_rate,
        pmi_rate=pmi_rate,
        pmi_equity_threshold=pmi_equity_threshold,
        purchase_price=purchase_price,
        refi_start_date=refi_start_date if show_refinance else None,
        refi_principal=refi_effective_principal,
        refi_years=refi_term_years,
        refi_periods_per_year=refi_periods_per_year if show_refinance else None,
        refi_rate_schedule=refi_rate_schedule,
        refi_mortgage_type=refi_mortgage_type,
        refi_mortgage_rate=refi_effective_rate
    )
    interest_saved_biweekly = monthly_comparison_df['Interest'].sum() - total_interest
    payoff_difference_biweekly = len(monthly_comparison_df) / 12 - payoff_years

cost_comparison_df = calculate_cost_comparison(
    main_annual_df,
    edited_property_expenses,
    edited_emergency_expenses,
    purchase_year,
    eval_start_year,
    eval_end_year,
    annual_appreciation,
    annual_insurance_increase,
    annual_maintenance_increase,
    annual_hoa_increase,
    cost_of_rent,
    annual_rent_increase,
    renters_insurance,
    security_deposit,
    points_cost,
    points_cost_method,
    closing_costs,
    closing_costs_method,
    refi_costs,
    roll_costs,
    refi_points_cost,
    refi_points_cost_method,
    rental_utilities,
    pet_fee,
    pet_fee_frequency,
    application_fee,
    lease_renewal_fee,
    parking_fee,
    purchase_price,
    vti_annual_return,
    down_payment
)

cost_comparison_df['Asset % Difference (Buy vs Rent)'] = np.where(
    cost_comparison_df['Renting Total Assets'] > 0,
    (cost_comparison_df['Buying Total Assets'] - cost_comparison_df['Renting Total Assets']) / cost_comparison_df['Renting Total Assets'] * 100,
    0
)

# Display
st.header("Mortgage Metrics")
scenario_text = f"{payment_frequency} Payments" + (" with Refinance" if show_refinance else "")
with st.container(border=True):
    st.markdown(f"<h3 style='margin: 0;'>{scenario_text}</h3>", unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Loan Amount", f"${loan_amount:,.0f}")
    cols[1].metric("% Down Payment", f"{percent_down:.2f}%")
    cols[2].metric("Monthly Payment", f"${monthly_payment:,.2f}")
    cols[3].metric("Payment per Period", f"${payment_per_period:,.2f}")
    cols = st.columns(4)
    cols[0].metric("Total Interest", f"${total_interest:,.2f}")
    cols[1].metric("Total PMI", f"${total_pmi:,.2f}")
    cols[2].metric("Payoff Year", payoff_year)
    cols[3].metric("Payoff Month", payoff_month)
if buy_points:
    cols = st.columns(2)
    cols[0].metric("Effective Rate After Points", f"{effective_rate:.3f}%", help="Rate after applying points discount.")
    cols[1].metric("Points Cost", f"${points_cost:,.2f}", help="Total cost of points purchased.")
if show_refinance and refi_buy_points:
    cols = st.columns(2)
    cols[0].metric("Refinance Effective Rate After Points", f"{refi_effective_rate:.3f}%", help="Refinance rate after points discount.")
    cols[1].metric("Refinance Points Cost", f"${refi_points_cost:,.2f}", help="Total cost of refinance points.")

if show_refinance and refi_start_date:
    st.header("Refinance Savings and Breakeven")
    with st.container(border=True):
        cols = st.columns(4)
        cols[0].metric("Interest Saved" if interest_saved_refi >= 0 else "Additional Interest", f"${abs(interest_saved_refi):,.2f}", help="Interest saved (or added) due to refinance.")
        cols[1].metric("PMI Saved" if pmi_saved_refi >= 0 else "Additional PMI", f"${abs(pmi_saved_refi):,.2f}", help="PMI saved (or added) due to refinance.")
        cols[2].metric("Payoff Time Difference", f"{abs(payoff_difference_refi):,.1f} years {'shorter' if payoff_difference_refi >= 0 else 'longer'}", help="Change in payoff time due to refinance.")
        if breakeven_years is not None:
            cols[3].metric("Breakeven Point", f"{breakeven_years:.1f} years ({breakeven_months:.1f} months)", help="Time until refinance savings offset upfront costs.")
        else:
            cols[3].metric("Breakeven Point", "Not applicable", help="No breakeven if refinance costs are financed or savings are insufficient.")

if payment_frequency == "Biweekly":
    st.header("Biweekly Savings")
    with st.container(border=True):
        cols = st.columns(2)
        cols[0].metric("Interest Saved" if interest_saved_biweekly >= 0 else "Additional Interest", f"${abs(interest_saved_biweekly):,.2f}", help="Interest saved due to biweekly payments.")
        cols[1].metric("Payoff Time Difference", f"{abs(payoff_difference_biweekly):,.1f} years {'shorter' if payoff_difference_biweekly >= 0 else 'longer'}", help="Payoff time reduction from biweekly payments.")

st.header("Amortization Schedule")
st.markdown("**Note**: 'Loan Type' indicates 'Original' (white) or 'Refinance' (blue). 'Effective Rate (%)' shows the applied interest rate.")
tab1, tab2 = st.tabs(["Annual", "Monthly"])
with tab1:
    st.dataframe(
        main_annual_df.style.format({
            "Date": "{:%Y}",
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra Principal Payments": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Effective Rate (%)": "{:.2f}%"
        }).apply(lambda row: ["background-color: #e6f3ff" if row["Loan Type"] == "Refinance" else ""] * len(row), axis=1),
        hide_index=True
    )
with tab2:
    st.dataframe(
        main_monthly_df.style.format({
            "Date": "{:%Y-%m}",
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra Principal Payments": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Effective Rate (%)": "{:.2f}%"
        }).apply(lambda row: ["background-color: #e6f3ff" if row["Loan Type"] == "Refinance" else ""] * len(row), axis=1),
        hide_index=True
    )

st.header("Amortization Breakdown")
main_schedule_df['Year'] = main_schedule_df['Date'].dt.year
no_extra_schedule_df['Year'] = no_extra_schedule_df['Date'].dt.year
main_annual = main_annual_df.copy()
main_annual['Year'] = main_annual['Date'].dt.year
no_extra_annual = no_extra_annual_df.copy()
no_extra_annual['Year'] = no_extra_annual['Date'].dt.year
main_annual['Cum Principal'] = main_annual['Principal'].cumsum()
main_annual['Cum Interest'] = main_annual['Interest'].cumsum()
main_annual['Cum PMI'] = main_annual['PMI'].cumsum()
no_extra_annual['Cum Principal'] = no_extra_annual['Principal'].cumsum()
no_extra_annual['Cum Interest'] = no_extra_annual['Interest'].cumsum()
no_extra_annual['Cum PMI'] = no_extra_annual['PMI'].cumsum()

tab1, tab2, tab3 = st.tabs(["By Payment", "By Year", "Cumulative Payoff"])
with tab1:
    fig_amort_payment = go.Figure()
    fig_amort_payment.add_trace(go.Scatter(x=main_schedule_df['Date'], y=main_schedule_df['Principal'], mode='lines', name='Principal (With Extra)', line=dict(dash='solid')))
    fig_amort_payment.add_trace(go.Scatter(x=main_schedule_df['Date'], y=main_schedule_df['Interest'], mode='lines', name='Interest (With Extra)', line=dict(dash='solid')))
    fig_amort_payment.add_trace(go.Scatter(x=no_extra_schedule_df['Date'], y=no_extra_schedule_df['Principal'], mode='lines', name='Principal (No Extra)', line=dict(dash='dot')))
    fig_amort_payment.add_trace(go.Scatter(x=no_extra_schedule_df['Date'], y=no_extra_schedule_df['Interest'], mode='lines', name='Interest (No Extra)', line=dict(dash='dot')))
    fig_amort_payment.add_trace(go.Bar(x=main_schedule_df['Date'], y=main_schedule_df['PMI'], name='PMI', yaxis='y2', opacity=0.4))
    fig_amort_payment.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Date', yaxis_title='Amount ($)', yaxis2=dict(overlaying='y', side='right', title='PMI ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        refi_timestamp = pd.Timestamp(refi_start_date).timestamp() * 1000
        fig_amort_payment.add_vline(x=refi_timestamp, line_dash="dash", line_color="red", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        payoff_timestamp = pd.Timestamp(f"{payoff_year}-01-01").timestamp() * 1000
        fig_amort_payment.add_vline(x=payoff_timestamp, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_amort_payment, use_container_width=True)

with tab2:
    fig_amort_year = go.Figure()
    fig_amort_year.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Principal'], mode='lines', name='Principal (With Extra)', line=dict(dash='solid')))
    fig_amort_year.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Interest'], mode='lines', name='Interest (With Extra)', line=dict(dash='solid')))
    fig_amort_year.add_trace(go.Scatter(x=no_extra_annual['Year'], y=no_extra_annual['Principal'], mode='lines', name='Principal (No Extra)', line=dict(dash='dot')))
    fig_amort_year.add_trace(go.Scatter(x=no_extra_annual['Year'], y=no_extra_annual['Interest'], mode='lines', name='Interest (No Extra)', line=dict(dash='dot')))
    fig_amort_year.add_trace(go.Bar(x=main_annual['Year'], y=main_annual['PMI'], name='PMI', yaxis='y2', opacity=0.4))
    fig_amort_year.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Amount ($)', yaxis2=dict(overlaying='y', side='right', title='PMI ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_amort_year.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_amort_year.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_amort_year, use_container_width=True)

with tab3:
    fig_amort_cum = go.Figure()
    fig_amort_cum.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Cum Principal'], mode='lines', name='Principal (With Extra)', line=dict(dash='solid')))
    fig_amort_cum.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Cum Interest'], mode='lines', name='Interest (With Extra)', line=dict(dash='solid')))
    fig_amort_cum.add_trace(go.Scatter(x=no_extra_annual['Year'], y=no_extra_annual['Cum Principal'], mode='lines', name='Principal (No Extra)', line=dict(dash='dot')))
    fig_amort_cum.add_trace(go.Scatter(x=no_extra_annual['Year'], y=no_extra_annual['Cum Interest'], mode='lines', name='Interest (No Extra)', line=dict(dash='dot')))
    fig_amort_cum.add_trace(go.Bar(x=main_annual['Year'], y=main_annual['Cum PMI'], name='PMI', yaxis='y2', opacity=0.4))
    fig_amort_cum.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Cumulative Amount ($)', yaxis2=dict(overlaying='y', side='right', title='PMI ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_amort_cum.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_amort_cum.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_amort_cum, use_container_width=True)

st.header("Savings from Extra Payments")
main_annual['Interest Saved'] = no_extra_annual['Cum Interest'] - main_annual['Cum Interest']
main_annual['PMI Saved'] = no_extra_annual['Cum PMI'] - main_annual['Cum PMI']
fig_saved_extra = go.Figure()
fig_saved_extra.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Interest Saved'], mode='lines+markers', name='Interest Saved'))
fig_saved_extra.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['PMI Saved'], mode='lines+markers', name='PMI Saved', yaxis='y2'))
fig_saved_extra.update_layout(
    plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
    xaxis_title='Year', yaxis_title='Interest Saved ($)', yaxis2=dict(overlaying='y', side='right', title='PMI Saved ($)'),
    legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
)
if show_refinance and refi_start_date:
    fig_saved_extra.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
    fig_saved_extra.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
st.plotly_chart(fig_saved_extra, use_container_width=True)

if payment_frequency == "Biweekly":
    st.header("Savings from Biweekly Payments")
    monthly_comp_annual = monthly_comparison_annual_df.copy()
    monthly_comp_annual['Year'] = monthly_comp_annual['Date'].dt.year
    monthly_comp_annual['Cum Interest'] = monthly_comp_annual['Interest'].cumsum()
    monthly_comp_annual['Cum PMI'] = monthly_comp_annual['PMI'].cumsum()
    main_annual['Cum Interest'] = main_annual['Interest'].cumsum()
    main_annual['Cum PMI'] = main_annual['PMI'].cumsum()
    main_annual['Interest Saved'] = monthly_comp_annual['Cum Interest'] - main_annual['Cum Interest']
    main_annual['PMI Saved'] = monthly_comp_annual['Cum PMI'] - main_annual['Cum PMI']
    fig_saved_bi = go.Figure()
    fig_saved_bi.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Interest Saved'], mode='lines+markers', name='Interest Saved'))
    fig_saved_bi.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['PMI Saved'], mode='lines+markers', name='PMI Saved', yaxis='y2'))
    fig_saved_bi.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Interest Saved ($)', yaxis2=dict(overlaying='y', side='right', title='PMI Saved ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_saved_bi.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_saved_bi.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_saved_bi, use_container_width=True)


st.markdown(
    """<hr style="height:4px;border:none;color:#333;background-color:#333;" /> """,
    unsafe_allow_html=True
)

st.header("Evaluation Year Selection")
with st.container(border=True):
    selected_year = st.selectbox(
        "Select Evaluation Year",
        options=list(range(eval_start_year, eval_end_year + 1)),
        index=0,
        help="Choose a year to view detailed asset and cost breakdowns."
    )

st.header("Asset Metrics")
st.markdown('<div class="highlight-box">Select a year to analyze asset and cost metrics. Buying assets include home equity, appreciation, and VTI investments. Renting assets include VTI investments from cost savings and down payment.</div>', unsafe_allow_html=True)
final_data = cost_comparison_df[cost_comparison_df["Year"] == selected_year]
if not final_data.empty:
    final_balance = main_annual_df[main_annual_df["Date"].dt.year == selected_year]["Balance"].iloc[-1] if selected_year in main_annual_df["Date"].dt.year.values else 0
    final_home_value = purchase_price * (1 + annual_appreciation / 100) ** (selected_year - purchase_year)
    equity_gain = final_data["Equity Gain"].iloc[0]
    appreciation = final_data["Appreciation"].iloc[0]
    buying_investment = final_data["Buying Investment"].iloc[0]
    renting_investment = final_data["Renting Investment"].iloc[0]
    buying_assets = final_data["Buying Total Assets"].iloc[0]
    renting_assets = final_data["Renting Total Assets"].iloc[0]
    asset_difference = buying_assets - renting_assets
else:
    year_idx = selected_year - purchase_year
    final_balance = 0
    final_home_value = purchase_price * (1 + annual_appreciation / 100) ** year_idx
    equity_gain = final_home_value
    appreciation = final_home_value - purchase_price
    last_year_data = cost_comparison_df[cost_comparison_df["Year"] == cost_comparison_df["Year"].max()]
    if not last_year_data.empty:
        last_year_idx = cost_comparison_df["Year"].max() - purchase_year
        years_diff = year_idx - last_year_idx
        buying_investment = last_year_data["Buying Investment"].iloc[0] * (1 + vti_annual_return / 100) ** years_diff
        renting_investment = last_year_data["Renting Investment"].iloc[0] * (1 + vti_annual_return / 100) ** years_diff
    else:
        buying_investment = 0
        renting_investment = 0
    buying_assets = equity_gain + buying_investment
    renting_assets = renting_investment
    asset_difference = buying_assets - renting_assets

buy_col, rent_col = st.columns(2)
with buy_col:
    st.markdown(f"### Buying Assets ({selected_year})")
    buy_asset_df = pd.DataFrame({
        "Item": ["Equity", "Appreciation", "Investment"],
        "Value": [equity_gain, appreciation, buying_investment]
    })
    buy_asset_df = buy_asset_df[buy_asset_df["Value"] > 0]
    total_buy = buy_asset_df["Value"].sum()
    buy_asset_df["% of Total"] = (buy_asset_df["Value"] / total_buy) * 100 if total_buy > 0 else 0
    total_buy_row = pd.DataFrame({"Item": ["Total"], "Value": [total_buy], "% of Total": [100.0]})
    buy_asset_df = pd.concat([buy_asset_df, total_buy_row], ignore_index=True)
    st.dataframe(
        buy_asset_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
        .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
        hide_index=True
    )
with rent_col:
    st.markdown(f"### Renting Assets ({selected_year})")
    rent_asset_df = pd.DataFrame({
        "Item": ["Investment"],
        "Value": [renting_investment]
    })
    rent_asset_df = rent_asset_df[rent_asset_df["Value"] > 0]
    total_rent = rent_asset_df["Value"].sum()
    rent_asset_df["% of Total"] = (rent_asset_df["Value"] / total_rent) * 100 if total_rent > 0 else 0
    total_rent_row = pd.DataFrame({"Item": ["Total"], "Value": [total_rent], "% of Total": [100.0]})
    rent_asset_df = pd.concat([rent_asset_df, total_rent_row], ignore_index=True)
    st.dataframe(
        rent_asset_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
        .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
        hide_index=True
    )
st.metric("Asset Difference (Buy - Rent)", f"${asset_difference:,.2f}", delta_color="normal")

st.divider()
st.header("Asset Breakdown")
buy_asset_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][['Equity Gain', 'Appreciation', 'Buying Investment']].melt(
    var_name='Category', value_name='Value'
)
buy_asset_data = buy_asset_data[buy_asset_data['Value'] > 0]
rent_asset_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][['Renting Investment']].melt(
    var_name='Category', value_name='Value'
)
rent_asset_data = rent_asset_data[rent_asset_data['Value'] > 0]

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Buying Assets")
    fig_buy_asset = px.treemap(
        buy_asset_data, path=['Category'], values='Value', color='Value', color_continuous_scale='Blues',
        labels={'Value': 'Value ($)'}, hover_data={'Value': ':.2f'}
    )
    fig_buy_asset.update_traces(texttemplate='%{label}<br>%{value:,.0f} (%{percentParent:.2%})')
    fig_buy_asset.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_buy_asset, use_container_width=True)
with col2:
    st.markdown("### Renting Assets")
    fig_rent_asset = px.treemap(
        rent_asset_data, path=['Category'], values='Value', color='Value', color_continuous_scale='Blues',
        labels={'Value': 'Value ($)'}, hover_data={'Value': ':.2f'}
    )
    fig_rent_asset.update_traces(texttemplate='%{label}<br>%{value:,.0f} (%{percentParent:.2%})')
    fig_rent_asset.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_rent_asset, use_container_width=True)

with st.expander("Detailed Asset Breakdown by Year", expanded=False):
    asset_breakout = cost_comparison_df[['Year', 'Equity Gain', 'Appreciation', 'Buying Investment', 'Buying Total Assets', 'Renting Investment', 'Renting Total Assets', 'Asset Difference (Buy - Rent)']]
    asset_breakout['Year'] = asset_breakout['Year'].astype(str)
    st.dataframe(asset_breakout.style.format({col: "${:,.2f}" for col in asset_breakout.columns if col != 'Year'}), hide_index=True)

st.header("Cost Metrics")
buy_cost_cols = ['Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs']
rent_cost_cols = ['Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee']
buy_cost_df = cost_comparison_df[cost_comparison_df['Year'] == selected_year][buy_cost_cols].melt(
    var_name='Item', value_name='Value'
)
buy_cost_df = buy_cost_df[buy_cost_df['Value'] > 0]
total_buy_cost = buy_cost_df['Value'].sum()
buy_cost_df['% of Total'] = (buy_cost_df['Value'] / total_buy_cost) * 100 if total_buy_cost > 0 else 0
total_buy_cost_row = pd.DataFrame({"Item": ["Total"], "Value": [total_buy_cost], "% of Total": [100.0]})
buy_cost_df = pd.concat([buy_cost_df, total_buy_cost_row], ignore_index=True)

rent_cost_df = cost_comparison_df[cost_comparison_df['Year'] == selected_year][rent_cost_cols].melt(
    var_name='Item', value_name='Value'
)
rent_cost_df = rent_cost_df[rent_cost_df['Value'] > 0]
total_rent_cost = rent_cost_df['Value'].sum()
rent_cost_df['% of Total'] = (rent_cost_df['Value'] / total_rent_cost) * 100 if total_rent_cost > 0 else 0
total_rent_cost_row = pd.DataFrame({"Item": ["Total"], "Value": [total_rent_cost], "% of Total": [100.0]})
rent_cost_df = pd.concat([rent_cost_df, total_rent_cost_row], ignore_index=True)

buy_col, rent_col = st.columns(2)
with buy_col:
    st.markdown(f"### Buying Costs ({selected_year})")
    st.dataframe(
        buy_cost_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
        .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
        hide_index=True
    )
with rent_col:
    st.markdown(f"### Renting Costs ({selected_year})")
    st.dataframe(
        rent_cost_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
        .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
        hide_index=True
    )

st.header("Cost Breakdown")
buy_cost_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][buy_cost_cols].melt(
    var_name='Category', value_name='Cost'
)
buy_cost_data = buy_cost_data[buy_cost_data['Cost'] > 0]
rent_cost_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][rent_cost_cols].melt(
    var_name='Category', value_name='Cost'
)
rent_cost_data = rent_cost_data[rent_cost_data['Cost'] > 0]

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Buying Costs")
    fig_buy_cost = px.treemap(
        buy_cost_data, path=['Category'], values='Cost', color='Cost', color_continuous_scale='Blues',
        labels={'Cost': 'Cost ($)'}, hover_data={'Cost': ':.2f'}
    )
    fig_buy_cost.update_traces(texttemplate='%{label}<br>%{value:,.0f} (%{percentParent:.2%})')
    fig_buy_cost.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_buy_cost, use_container_width=True)
with col2:
    st.markdown("### Renting Costs")
    fig_rent_cost = px.treemap(
        rent_cost_data, path=['Category'], values='Cost', color='Cost', color_continuous_scale='Blues',
        labels={'Cost': 'Cost ($)'}, hover_data={'Cost': ':.2f'}
    )
    fig_rent_cost.update_traces(texttemplate='%{label}<br>%{value:,.0f} (%{percentParent:.2%})')
    fig_rent_cost.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_rent_cost, use_container_width=True)

st.header("Costs")
tab_non_cum, tab_cum = st.tabs(["By Period", "Cumulative"])
with tab_non_cum:
    cost_data = pd.concat([
        pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Cost": cost_comparison_df["Total Buying Cost"],
            "Type": "Buying"
        }),
        pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Cost": cost_comparison_df["Total Renting Cost"],
            "Type": "Renting"
        })
    ])
    fig_costs = px.line(cost_data, x='Year', y='Cost', color='Type', markers=True)
    fig_costs.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Annual Cost ($)',
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_costs.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
        fig_costs.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_costs.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_costs, use_container_width=True)

with tab_cum:
    cum_cost_data = pd.concat([
        pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Cost": cost_comparison_df["Cumulative Buying Cost"],
            "Type": "Buying"
        }),
        pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Cost": cost_comparison_df["Cumulative Renting Cost"],
            "Type": "Renting"
        })
    ])
    fig_cum_costs = px.line(cum_cost_data, x='Year', y='Cost', color='Type', markers=True)
    fig_cum_costs.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Cumulative Cost ($)',
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_cum_costs.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
        fig_cum_costs.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_cum_costs.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_cum_costs, use_container_width=True)

st.divider()
st.header("One-time vs. Repeating Costs")
buy_cost_types = pd.DataFrame({
    'Year': cost_comparison_df['Year'],
    'One-time': cost_comparison_df['Closing Costs'] + cost_comparison_df['Points Costs'] + cost_comparison_df['Emergency'],
    'Repeating': cost_comparison_df['Direct Costs (P&I)'] + cost_comparison_df['PMI'] + cost_comparison_df['Property Taxes'] + cost_comparison_df['Home Insurance'] + cost_comparison_df['Maintenance'] + cost_comparison_df['HOA Fees']
})
rent_cost_types = pd.DataFrame({
    'Year': cost_comparison_df['Year'],
    'One-time': cost_comparison_df['Security Deposit'] + cost_comparison_df['Application Fee'] + (cost_comparison_df['Pet Fees'] if pet_fee_frequency == "One-time" else 0),
    'Repeating': cost_comparison_df['Rent'] + cost_comparison_df['Renters Insurance'] + cost_comparison_df['Utilities'] + cost_comparison_df['Lease Renewal Fee'] + cost_comparison_df['Parking Fee'] + (cost_comparison_df['Pet Fees'] if pet_fee_frequency == "Annual" else 0)
})

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Buying Costs")
    fig_buy_cost_types = go.Figure()
    fig_buy_cost_types.add_trace(go.Bar(x=buy_cost_types['Year'], y=buy_cost_types['One-time'], name='One-time'))
    fig_buy_cost_types.add_trace(go.Bar(x=buy_cost_types['Year'], y=buy_cost_types['Repeating'], name='Repeating'))
    fig_buy_cost_types.update_layout(
        barmode='stack',
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Cost ($)',
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_buy_cost_types.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
        fig_buy_cost_types.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_buy_cost_types.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_buy_cost_types, use_container_width=True)

with col2:
    st.markdown("### Renting Costs")
    fig_rent_cost_types = go.Figure()
    fig_rent_cost_types.add_trace(go.Bar(x=rent_cost_types['Year'], y=rent_cost_types['One-time'], name='One-time'))
    fig_rent_cost_types.add_trace(go.Bar(x=rent_cost_types['Year'], y=rent_cost_types['Repeating'], name='Repeating'))
    fig_rent_cost_types.update_layout(
        barmode='stack',
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Cost ($)',
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    st.plotly_chart(fig_rent_cost_types, use_container_width=True)

with st.expander("Detailed Costs Breakdown by Year", expanded=False):
    cost_breakout = cost_comparison_df[['Year', 'Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs', 'Total Buying Cost', 'Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee', 'Total Renting Cost', 'Cost Difference (Buy - Rent)']]
    cost_breakout['Year'] = cost_breakout['Year'].astype(str)
    st.dataframe(cost_breakout.style.format({col: "${:,.2f}" for col in cost_breakout.columns if col != 'Year'}), hide_index=True)
st.header("Net Asset Value Over Time")
net_asset_data = pd.concat([
    pd.DataFrame({
        "Year": cost_comparison_df["Year"],
        "Net Assets": cost_comparison_df["Buying Total Assets"] - cost_comparison_df["Cumulative Buying Cost"],
        "Type": "Buying"
    }),
    pd.DataFrame({
        "Year": cost_comparison_df["Year"],
        "Net Assets": cost_comparison_df["Renting Total Assets"] - cost_comparison_df["Cumulative Renting Cost"],
        "Type": "Renting"
    })
])
fig_net_assets = px.line(net_asset_data, x='Year', y='Net Assets', color='Type', markers=True)
fig_net_assets.update_layout(
    plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
    xaxis_title='Year', yaxis_title='Net Assets ($)',
    legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
)
if show_refinance and refi_start_date:
    fig_net_assets.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
    fig_net_assets.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
    fig_net_assets.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
st.plotly_chart(fig_net_assets, use_container_width=True)