# ----------------------------- IMPORTS -----------------------------
import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import datetime, timedelta
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import time

# Custom CSS for smaller font sizes in metrics and tables
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        font-size: 16px !important;
    }
    .dataframe td, .dataframe th {
        font-size: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------- PAGE CONFIG -----------------------------
st.set_page_config(page_title="Rent vs. Buy Decision Support Framework", layout="wide")
st.title("Rent vs. Buy Decision Support Framework")

# ----------------------------- INSTRUCTIONS -----------------------------
with st.expander("Welcome & Instructions", expanded=False):
    st.markdown("""
    This dashboard empowers you to make an informed **rent vs. buy** decision by analyzing all costs and asset growth associated with homeownership and renting, with stunning visualizations to highlight financial impacts.

    **Key Outputs:**
    - **Unified Amortization Schedule**: Monthly or biweekly, with refinance transition (if enabled).
    - **Main Metrics**: Payment details, total interest, PMI, and payoff time.
    - **Refinance Analysis**: Interest, PMI, and payoff time savings, with breakeven point.
    - **Biweekly Savings**: Interest saved and payoff reduction (if biweekly selected).
    - **Cost Comparison**: Buying (P&I, PMI, taxes, insurance, maintenance, emergency, HOA, closing/points) vs. renting (rent, insurance, deposits, utilities, pet fees, application/renewal/parking).
    - **Asset Comparison**: Homeowner wealth (home equity + VTI investments) vs. renter wealth (VTI investments from cost savings).
    - **Visualizations**: Line charts for costs, bar charts for cost breakdowns, interactive tables.

    **How to Use:**
    1. Enter purchase details, loan terms, mortgage type, and renting assumptions.
    2. Specify extra payments, buy points, refinance options, and VTI return rate.
    3. Explore metrics, schedules, savings, costs, and asset growth.
    4. Interact with charts (hover for details) and download data.

    **Methodology:**
    - Payments: Monthly (12/year), Biweekly (26/year).
    - Variable-rate mortgages adjust via rate schedules.
    - Extra payments reduce principal consistently.
    - Points reduce rates (1 point = 1% of loan amount).
    - Costs: Buying includes direct (P&I) and indirect (PMI, taxes, etc.); renting includes rent, fees, etc.
    - Investments: Cost differences (buying vs. renting) are invested in VTI (default 7% annual return). In the rent scenario, the down payment and any upfront costs not incurred are invested.
    - Equity: Homeowners gain equity from appreciation and principal; renters invest savings in VTI.
    """)

# ----------------------------- SIDEBAR -----------------------------
with st.sidebar.container():
    st.image("images/EyesWideOpenLogo.png", use_container_width=False, width=300)
    st.markdown("Tool developed by Eric Hubbard")
    st.markdown("[KnowTheCostFinancial.com](https://knowthecostfinancial.com)")

    st.markdown("---")

    # Define defaults to avoid NameError
    purchase_year = 2025  # Default value
    loan_years = 30       # Default value

    st.sidebar.header("Buying Parameters")

    # Purchase Details
    with st.expander("Purchase Details", expanded=True):
        purchase_year = st.number_input("Purchase Year", value=purchase_year, step=1, min_value=2000, max_value=2100)
        purchase_price = st.number_input("Purchase Price ($)", value=500_000, step=10_000, min_value=0)
        down_payment = st.number_input("Down Payment ($)", value=100_000, step=1_000, min_value=0, max_value=purchase_price)
        closing_costs = st.number_input("Closing Costs ($)", value=5000, step=500, min_value=0)
        closing_costs_method = st.selectbox("Closing Costs Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
        loan_amount = purchase_price - down_payment + (closing_costs if closing_costs_method == "Add to Loan Balance" else 0)
        percent_down = (down_payment / purchase_price * 100) if purchase_price > 0 else 0

    # Loan Terms & Mortgage
    with st.expander("Loan Terms & Mortgage", expanded=True):
        loan_years = st.number_input("Loan Length (Years)", value=loan_years, step=1, min_value=1, max_value=50)
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.01, min_value=0.0, format="%.3f")
        pmi_rate = st.number_input("PMI Rate (%)", value=0.20, step=0.01, min_value=0.0)
        pmi_equity_threshold = st.number_input("PMI Paid Until Equity (%)", value=20, step=1, min_value=0, max_value=100)
        payment_frequency = st.selectbox("Payment Frequency", ["Monthly", "Biweekly"], index=0)
        mortgage_type = st.selectbox("Mortgage Type", ["Fixed", "Variable"], index=0)

        # Buy Points Option
        buy_points = st.checkbox("Buy Points to Reduce Rate?", value=False)
        points = 0
        discount_per_point = 0.25
        points_cost_method = "Add to Loan Balance"
        points_cost = 0
        effective_rate = mortgage_rate
        if buy_points:
            points = st.number_input("Number of Points", value=1.0, step=0.25, min_value=0.0)
            discount_per_point = st.number_input("Rate Discount per Point (%)", value=0.25, step=0.01, min_value=0.0)
            points_cost_method = st.selectbox("Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
            effective_rate = mortgage_rate - (discount_per_point * points)
            points_cost = points * (purchase_price - down_payment) * 0.01
            st.metric("Effective Rate After Points", f"{effective_rate:.3f}%")
            st.metric("Points Cost", f"${points_cost:,.2f}")

        rate_schedule = None
        if mortgage_type == "Variable":
            st.subheader("Variable Rate Schedule")
            default_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [mortgage_rate, 6.5, 7.0]})
            rate_schedule = st.data_editor(
                default_schedule,
                column_config={
                    "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=loan_years, step=1),
                    "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1)
                },
                hide_index=True,
                num_rows="dynamic"
            )

    # Refinance Options
    with st.expander("Refinance Options", expanded=False):
        show_refinance = st.checkbox("Model a Refinance?", value=False)
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
            refi_rate = st.number_input("Refinance Rate (%)", value=4.0, step=0.01, min_value=0.0, format="%.3f")
            refi_term_years = st.number_input("Refinance Term (Years)", value=20, step=1, min_value=1, max_value=50)
            refi_start_date = st.date_input("Refinance Start Date", min_value=datetime(purchase_year, 1, 1), max_value=datetime(purchase_year + loan_years, 12, 31))
            refi_costs = st.number_input("Refinance Closing Costs ($)", value=3000, step=500, min_value=0)
            roll_costs = st.selectbox("Refinance Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
            refi_payment_frequency = st.selectbox("Refinance Payment Frequency", ["Monthly", "Biweekly"], index=0)
            refi_mortgage_type = st.selectbox("Refinance Mortgage Type", ["Fixed", "Variable"], index=0)
            refi_periods_per_year = 12 if refi_payment_frequency == "Monthly" else 26
            refi_effective_rate = refi_rate

            refi_buy_points = st.checkbox("Buy Points for Refinance?", value=False)
            if refi_buy_points:
                refi_points = st.number_input("Refinance Points", value=1.0, step=0.25, min_value=0.0)
                refi_discount_per_point = st.number_input("Refinance Rate Discount per Point (%)", value=0.25, step=0.01, min_value=0.0)
                refi_points_cost_method = st.selectbox("Refinance Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
                refi_effective_rate = refi_rate - (refi_discount_per_point * refi_points)
                refi_points_cost = refi_points * (purchase_price - down_payment) * 0.01
                st.metric("Refinance Effective Rate After Points", f"{refi_effective_rate:.3f}%")
                st.metric("Refinance Points Cost", f"${refi_points_cost:,.2f}")

            if refi_mortgage_type == "Variable":
                st.subheader("Refinance Variable Rate Schedule")
                default_refi_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [refi_effective_rate, 5.5, 6.0]})
                refi_rate_schedule = st.data_editor(
                    default_refi_schedule,
                    column_config={
                        "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=refi_term_years, step=1),
                        "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1)
                    },
                    hide_index=True,
                    num_rows="dynamic"
                )

    # Extra Principal Payments
    with st.expander("Extra Principal Payments", expanded=False):
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
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100),
                "Frequency": st.column_config.SelectboxColumn("Frequency", options=["One-time", "Monthly", "Quarterly", "Annually", "Every X Years"]),
                "Start Year": st.column_config.NumberColumn("Start Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1),
                "Start Month": st.column_config.NumberColumn("Start Month", min_value=1, max_value=12, step=1),
                "End Year": st.column_config.NumberColumn("End Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1),
                "End Month": st.column_config.NumberColumn("End Month", min_value=1, max_value=12, step=1),
                "Interval (Years)": st.column_config.NumberColumn("Interval (Years)", min_value=1, step=1)
            },
            hide_index=True,
            num_rows="dynamic"
        )

    # Appreciation & Growth
    with st.expander("Appreciation & Growth", expanded=False):
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=3.5, step=0.1, min_value=0.0)
        annual_maintenance_increase = st.number_input("Annual Maintenance Increase (%)", value=3.0, step=0.1, min_value=0.0)
        annual_insurance_increase = st.number_input("Annual Insurance Increase (%)", value=3.0, step=0.1, min_value=0.0)
        annual_hoa_increase = st.number_input("Annual HOA Increase (%)", value=3.0, step=0.1, min_value=0.0)
        vti_annual_return = st.number_input("Annual VTI Return (%)", value=7.0, step=0.1, min_value=0.0, help="Annual return rate for investments in a low-cost index fund (e.g., VTI).")

    st.sidebar.header("Ongoing Expenses")

    # Ongoing Expenses
    with st.expander("Ongoing Expenses", expanded=False):
        st.subheader("Regular Expenses")
        default_property_expenses = pd.DataFrame({
            "Category": ["Property Taxes", "Home Insurance", "Routine Maintenance", "HOA Fees"],
            "Amount ($)": [8000, 1100, 6000, 1200]
        })
        edited_property_expenses = st.data_editor(
            default_property_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category"),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100)
            },
            hide_index=True,
            num_rows="dynamic"
        )

        st.subheader("Emergency Expenses")
        default_emergency_expenses = pd.DataFrame({
            "Category": ["Appliance Replacement", "Septic Repair", "Roof Repair"],
            "Amount ($)": [1500, 8000, 12000],
            "Year": [purchase_year + 1, purchase_year + 5, purchase_year + 10],
            "Month": [5, 7, 9]
        })
        edited_emergency_expenses = st.data_editor(
            default_emergency_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category"),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100),
                "Year": st.column_config.NumberColumn("Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1),
                "Month": st.column_config.NumberColumn("Month", min_value=1, max_value=12, step=1)
            },
            hide_index=True,
            num_rows="dynamic"
        )

    st.sidebar.header("Rental Parameters")

    # Rental Assumptions
    with st.expander("Rental Assumptions", expanded=False):
        cost_of_rent = st.number_input("Initial Monthly Rent ($)", value=3000, step=50, min_value=0)
        annual_rent_increase = st.number_input("Annual Rent Increase (%)", value=3.0, step=0.1, min_value=0.0)
        renters_insurance = st.number_input("Annual Renters' Insurance ($)", value=300, step=50, min_value=0)
        security_deposit = st.number_input("Security Deposit ($)", value=3000, step=100, min_value=0)
        annual_deposit_increase = st.number_input("Annual Deposit Increase (%)", value=0.0, step=0.1, min_value=0.0, help="Increase applied to security deposit if renewed annually; set to 0 if no increase.")
        rental_utilities = st.number_input("Annual Rental Utilities ($)", value=2400, step=100, min_value=0)
        pet_fee = st.number_input("Pet Fee/Deposit ($)", value=500, step=50, min_value=0)
        pet_fee_frequency = st.selectbox("Pet Fee Frequency", ["One-time", "Annual"], index=0)
        application_fee = st.number_input("Application Fee ($)", value=50, step=10, min_value=0)
        lease_renewal_fee = st.number_input("Annual Lease Renewal Fee ($)", value=200, step=50, min_value=0)
        parking_fee = st.number_input("Monthly Parking Fee ($)", value=100, step=10, min_value=0)

# Define default evaluation period
eval_start_year = 2025  # Default value
eval_end_year = 2070    # Default value

# ----------------------------- FUNCTIONS -----------------------------
@st.cache_data
def expand_extra_payments(df, start_year, loan_years, frequency):
    extra_schedule = {}
    start_date = datetime(start_year, 1, 1)
    periods_per_year = 12 if frequency == "Monthly" else 26
    n_payments = loan_years * periods_per_year
    delta = pd.DateOffset(months=1) if frequency == "Monthly" else timedelta(days=14)
    payment_dates = [start_date + i * delta for i in range(n_payments)]

    for _, row in df.iterrows():
        amt = row["Amount ($)"]
        freq = row["Frequency"]
        start_y = int(row["Start Year"])
        start_m = int(row["Start Month"])
        end_y = int(row["End Year"])
        end_m = int(row["End Month"])
        interval = int(row["Interval (Years)"]) if not pd.isna(row["Interval (Years)"]) else 1

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
                # For biweekly, split the extra over matching dates if freq is Monthly
                if freq == "Monthly" and frequency == "Biweekly" and len(matching_dates) > 1:
                    split_amt = amt / len(matching_dates)
                    for pdate in matching_dates:
                        extra_schedule[pdate] = extra_schedule.get(pdate, 0) + split_amt
                else:
                    apply_pdate = min(matching_dates, key=lambda x: abs((x - apply_date).days))
                    extra_schedule[apply_pdate] = extra_schedule.get(apply_pdate, 0) + amt

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

    # Initialize rate schedule
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

    # Calculate periods
    n_periods = years * periods_per_year
    if refi_start_date and refi_years and refi_periods_per_year:
        refi_start_period = int(((refi_start_date - start_date).days / 365.25) * periods_per_year)
        n_periods = max(n_periods, refi_start_period + refi_years * refi_periods_per_year)

    delta = pd.DateOffset(months=1) if periods_per_year == 12 else timedelta(days=14)
    refi_delta = pd.DateOffset(months=1) if refi_periods_per_year == 12 else timedelta(days=14) if refi_periods_per_year else delta

    # Initialize payment
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

        # Handle refinance
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

        # Update rate for variable mortgage
        applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
        current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else (refi_mortgage_rate / 100 if is_refinanced and refi_mortgage_rate else mortgage_rate / 100)

        if mortgage_type == "Variable" and n > 0:
            remaining_periods = (years if not is_refinanced else refi_years) * periods_per_year - n
            monthly_payment = npf.pmt(current_rate / 12, remaining_periods / (periods_per_year / 12), -balance)
            payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

        # Calculate PMI
        equity = (purchase_price - balance) / purchase_price * 100 if purchase_price > 0 else 0
        pmi_payment = round((principal * pmi_rate / 100 / 12), 2) if equity < pmi_equity_threshold else 0

        # Apply extra payment
        extra = 0
        if extra_schedule:
            closest_date = min(extra_schedule.keys(), key=lambda x: abs((x - current_date).days), default=None)
            if closest_date and abs((closest_date - current_date).days) <= (30 if periods_per_year == 12 else 14):
                extra = extra_schedule.get(closest_date, 0)

        # Calculate payment components
        interest = round(balance * (current_rate / periods_per_year), 2)
        principal_paid = round(payment - interest, 2)

        if principal_paid + extra > balance:
            principal_paid = round(balance - extra, 2)
            payment = round(principal_paid + interest, 2)

        balance = round(balance - (principal_paid + extra), 2)

        schedule.append({
            "Payment #": n + 1,
            "Date": current_date,
            "Payment": payment,
            "Interest": interest,
            "Principal": principal_paid,
            "Extra": extra,
            "PMI": pmi_payment,
            "Balance": balance,
            "Loan Type": "Refinance" if is_refinanced else "Original",
            "Effective Rate (%)": current_rate * 100
        })

        if balance <= 0:
            break

    df = pd.DataFrame(schedule)
    df_monthly = df.groupby(df["Date"].dt.to_period("M")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Payment #": "count",
        "Loan Type": "last",
        "Effective Rate (%)": "last"
    }).reset_index()
    df_monthly.rename(columns={"Payment #": "Num Payments"}, inplace=True)
    df_monthly["Date"] = df_monthly["Date"].dt.to_timestamp()

    df_annual = df.groupby(df["Date"].dt.to_period("Y")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Payment #": "count",
        "Loan Type": "last",
        "Effective Rate (%)": "last"
    }).reset_index()
    df_annual.rename(columns={"Payment #": "Num Payments"}, inplace=True)
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
    annual_deposit_increase, 
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
    # Extend years to include full evaluation range
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
    rent_investment = down_payment  # Invest down payment in rent scenario

    for year in years:
        year_idx = year - purchase_year
        # Only include P&I and PMI if year is within loan term and mortgage is not paid off
        if year <= purchase_year + loan_years and year in annual_df["Date"].dt.year.values:
            p_and_i = annual_df[annual_df["Date"].dt.year == year]["Payment"].sum() + annual_df[annual_df["Date"].dt.year == year]["Extra"].sum() + annual_df[annual_df["Date"].dt.year == year]["Principal"].sum()
            pmi = annual_df[annual_df["Date"].dt.year == year]["PMI"].sum()
            year_balance = annual_df[annual_df["Date"].dt.year == year]["Balance"].iloc[-1]
        else:
            p_and_i = 0
            pmi = 0
            year_balance = 0  # Mortgage is paid off

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
        year_deposit = current_deposit if year == purchase_year else 0  # Only first year
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

        # Investment Calculations
        cost_difference = buy_cost - rent_cost
        if cost_difference > 0:  # Renting is cheaper
            rent_investment = rent_investment * (1 + vti_annual_return / 100) + cost_difference if cost_difference != 0 else rent_investment * (1 + vti_annual_return / 100)
            buy_investment = buy_investment * (1 + vti_annual_return / 100)
        else:  # Buying is cheaper
            buy_investment = buy_investment * (1 + vti_annual_return / 100) + abs(cost_difference) if cost_difference != 0 else buy_investment * (1 + vti_annual_return / 100)
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
        current_deposit *= (1 + annual_deposit_increase / 100)
        current_utilities *= (1 + annual_rent_increase / 100)
        current_pet_fee *= (1 + annual_deposit_increase / 100)
        current_parking *= (1 + annual_rent_increase / 100)

    return pd.DataFrame(comparison_data)

def get_remaining_balance(schedule_df, refi_date):
    refi_date = pd.to_datetime(refi_date)
    mask = schedule_df["Date"] <= refi_date
    return schedule_df.loc[mask, "Balance"].iloc[-1] if mask.any() else schedule_df["Balance"].iloc[0]

def calculate_breakeven(no_refi_monthly_df, main_monthly_df, refi_costs, refi_points_cost, roll_costs, refi_points_cost_method):
    if roll_costs == "Pay Upfront" or refi_points_cost_method == "Pay Upfront":
        total_costs = (refi_costs if roll_costs == "Pay Upfront" else 0) + (refi_points_cost if refi_points_cost_method == "Pay Upfront" else 0)
        monthly_savings = (no_refi_monthly_df["Payment"].iloc[0] + no_refi_monthly_df["PMI"].iloc[0]) - (main_monthly_df["Payment"].iloc[0] + main_monthly_df["PMI"].iloc[0])
        if monthly_savings > 0:
            breakeven_months = total_costs / monthly_savings
            breakeven_years = breakeven_months / 12
            return breakeven_years, breakeven_months
        else:
            return None, None
    return None, None

# ----------------------------- CALCULATIONS -----------------------------
# Adjust principal and rate based on points
effective_principal = loan_amount + (points_cost if points_cost_method == "Add to Loan Balance" else 0)
effective_mortgage_rate = effective_rate

# Extra payments schedules
extra_schedule = expand_extra_payments(extra_payments, purchase_year, loan_years, payment_frequency)
extra_schedule_monthly = expand_extra_payments(extra_payments, purchase_year, loan_years, "Monthly")
extra_schedule_biweekly = expand_extra_payments(extra_payments, purchase_year, loan_years, "Biweekly")

# No-refi schedule (always monthly, for refinance comparison)
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

# Refinance principal
refi_effective_principal = None
if show_refinance:
    refi_effective_principal = get_remaining_balance(no_refi_schedule_df, refi_start_date) + (refi_costs if roll_costs == "Add to Loan Balance" else 0) + (refi_points_cost if refi_points_cost_method == "Add to Loan Balance" else 0)

# Monthly comparison schedule (for biweekly savings)
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

# Biweekly comparison schedule
biweekly_schedule_df, biweekly_monthly_df, biweekly_annual_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=26,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=extra_schedule_biweekly,
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

# Main schedule (monthly or biweekly)
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

# No extra schedule
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

# Main Metrics
monthly_payment = main_schedule_df['Payment'].iloc[0] if main_periods_per_year == 12 else main_schedule_df['Payment'].iloc[0] * 26 / 12
payment_per_period = main_schedule_df['Payment'].iloc[0]
total_interest = main_schedule_df['Interest'].sum()
total_pmi = main_schedule_df['PMI'].sum()
payoff_years = len(main_schedule_df) / main_periods_per_year

# Payoff date
payoff_date = main_schedule_df[main_schedule_df['Balance'] <= 0]['Date'].min() if (main_schedule_df['Balance'] <= 0).any() else main_schedule_df['Date'].max()
payoff_year = payoff_date.year
payoff_month = payoff_date.month

# Refinance Savings and Breakeven
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

# Biweekly Savings
interest_saved_biweekly = 0
payoff_difference_biweekly = 0
if payment_frequency == "Biweekly":
    interest_saved_biweekly = monthly_comparison_df['Interest'].sum() - total_interest
    payoff_difference_biweekly = len(monthly_comparison_df) / 12 - payoff_years

# Cost Comparison
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
    annual_deposit_increase, 
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
    down_payment=down_payment
)

# Calculate Payoff Year
payoff_year = main_annual_df[main_annual_df["Balance"] <= 0]["Date"].dt.year.min() if (main_annual_df["Balance"] <= 0).any() else None

# Calculate % Difference
cost_comparison_df['Asset % Difference (Buy vs Rent)'] = np.where(cost_comparison_df['Renting Total Assets'] > 0,
                                                                  (cost_comparison_df['Buying Total Assets'] - cost_comparison_df['Renting Total Assets']) / cost_comparison_df['Renting Total Assets'] * 100,
                                                                  0)

# ----------------------------- DISPLAY -----------------------------
st.subheader("Mortgage Metrics")
scenario_text = "Main Scenario" + (" (with Refinance)" if show_refinance else " (Original Loan)") + f" ({payment_frequency} Payments)"
with st.container(border=True):
    st.markdown(f"<h3 style='margin: 0;'>{scenario_text}</h3>", unsafe_allow_html=True)
    cols = st.columns(5)
    cols[0].metric("Monthly Payment", f"${monthly_payment:,.2f}")
    cols[1].metric("Payment per Period", f"${payment_per_period:,.2f}")
    cols[2].metric("Total Interest", f"${total_interest:,.2f}")
    cols[3].metric("Total PMI", f"${total_pmi:,.2f}")
    cols[4].metric("Payoff Years", f"{payoff_years:.1f}")
    cols = st.columns(5)
    cols[0].metric("Loan Amount", f"${loan_amount:,.0f}")
    cols[1].metric("% Down Payment", f"{percent_down:.2f}%")
    cols[2].metric("Payoff Year", payoff_year)
    cols[3].metric("Payoff Month", payoff_month)

if show_refinance and refi_start_date:
    st.markdown("### Refinance Savings and Breakeven")
    with st.container(border=True):
        cols = st.columns(4)
        if interest_saved_refi >= 0:
            cols[0].metric("Interest Saved", f"${interest_saved_refi:,.2f}")
        else:
            cols[0].metric("Additional Interest", f"${abs(interest_saved_refi):,.2f}")
        if pmi_saved_refi >= 0:
            cols[1].metric("PMI Saved", f"${pmi_saved_refi:,.2f}")
        else:
            cols[1].metric("Additional PMI", f"${abs(pmi_saved_refi):,.2f}")
        cols[2].metric("Payoff Time Difference", f"{abs(payoff_difference_refi):,.1f} years {'shorter' if payoff_difference_refi >= 0 else 'longer'}")
        if breakeven_years is not None:
            cols[3].metric("Breakeven Point", f"{breakeven_years:.1f} years ({breakeven_months:.1f} months)")
        else:
            cols[3].metric("Breakeven Point", "Not applicable (no savings)")

if payment_frequency == "Biweekly":
    st.markdown("### Biweekly Savings (Compared to Monthly)")
    with st.container(border=True):
        cols = st.columns(2)
        if interest_saved_biweekly >= 0:
            cols[0].metric("Interest Saved", f"${interest_saved_biweekly:,.2f}")
        else:
            cols[0].metric("Additional Interest", f"${abs(interest_saved_biweekly):,.2f}")
        cols[1].metric("Payoff Time Difference", f"{abs(payoff_difference_biweekly):,.1f} years {'shorter' if payoff_difference_biweekly >= 0 else 'longer'}")

st.subheader("Amortization Schedule")
st.markdown("**Note**: 'Loan Type' column indicates 'Original' or 'Refinance' (highlighted in blue). 'Effective Rate (%)' shows the interest rate applied, reflecting points or variable rates.")
tab1, tab2 = st.tabs(["Annual", "Monthly"])

with tab1:
    st.dataframe(
        main_annual_df.style.format({
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Effective Rate (%)": "{:.3f}%",
            "Date": "{:%Y}"
        }).apply(lambda row: ["background-color: #e6f3ff; font-weight: bold" if row["Loan Type"] == "Refinance" else "font-weight: bold" if row.name == "Loan Type" else ""] * len(row), axis=1),
        hide_index=True
    )

with tab2:
    st.dataframe(
        main_monthly_df.style.format({
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Effective Rate (%)": "{:.3f}%",
            "Date": "{:%Y-%m}"
        }).apply(lambda row: ["background-color: #ffe699" if row["Num Payments"] > 1 else "background-color: #e6f3ff; font-weight: bold" if row["Loan Type"] == "Refinance" else "font-weight: bold" if row.name == "Loan Type" else ""] * len(row), axis=1),
        hide_index=True
    )

st.subheader("Amortization Breakdown")
main_annual = main_annual_df.copy()
main_annual['Year'] = main_annual['Date'].dt.year
no_extra_annual = no_extra_annual_df.copy()
no_extra_annual['Year'] = no_extra_annual['Date'].dt.year

fig_amort = go.Figure()
fig_amort.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Principal'], mode='lines', name='Principal (with extra)', line=dict(dash='solid')))
fig_amort.add_trace(go.Scatter(x=main_annual['Year'], y=main_annual['Interest'], mode='lines', name='Interest (with extra)', line=dict(dash='solid')))
fig_amort.add_trace(go.Scatter(x=no_extra_annual['Year'], y=no_extra_annual['Principal'], mode='lines', name='Principal (no extra)', line=dict(dash='dot')))
fig_amort.add_trace(go.Scatter(x=no_extra_annual['Year'], y=no_extra_annual['Interest'], mode='lines', name='Interest (no extra)', line=dict(dash='dot')))
fig_amort.add_trace(go.Bar(x=main_annual['Year'], y=main_annual['PMI'], name='PMI', yaxis='y2'))
fig_amort.update_layout(
    plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
    title_font_size=28, font=dict(family="Arial", size=14, color="black"),
    yaxis2=dict(overlaying='y', side='right'),
    xaxis_title='Year',
    yaxis_title='Amount ($)'
)
st.plotly_chart(fig_amort, use_container_width=True)

st.subheader("Savings from Extra Payments")
main_annual['Cum Interest With'] = main_annual['Interest'].cumsum()
main_annual['Cum PMI With'] = main_annual['PMI'].cumsum()
no_extra_annual['Cum Interest No'] = no_extra_annual['Interest'].cumsum()
no_extra_annual['Cum PMI No'] = no_extra_annual['PMI'].cumsum()
main_annual['Interest Saved'] = no_extra_annual['Cum Interest No'] - main_annual['Cum Interest With']
main_annual['PMI Saved'] = no_extra_annual['Cum PMI No'] - main_annual['Cum PMI With']
fig_saved_extra = px.line(main_annual, x='Year', y=['Interest Saved', 'PMI Saved'], title=None, markers=True)
fig_saved_extra.update_layout(
    plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
    title_font_size=28, font=dict(family="Arial", size=14, color="black"),
    xaxis_title='Year',
    yaxis_title='Savings ($)'
)
st.plotly_chart(fig_saved_extra, use_container_width=True)

if payment_frequency == "Biweekly":
    st.subheader("Savings from Biweekly Payments")
    monthly_comp_annual = monthly_comparison_annual_df.copy()
    monthly_comp_annual['Year'] = monthly_comp_annual['Date'].dt.year
    monthly_comp_annual['Cum Interest'] = monthly_comp_annual['Interest'].cumsum()
    monthly_comp_annual['Cum PMI'] = monthly_comp_annual['PMI'].cumsum()
    bi_annual = biweekly_annual_df.copy()
    bi_annual['Year'] = bi_annual['Date'].dt.year
    bi_annual['Cum Interest'] = bi_annual['Interest'].cumsum()
    bi_annual['Cum PMI'] = bi_annual['PMI'].cumsum()
    bi_annual['Interest Saved'] = monthly_comp_annual['Cum Interest'] - bi_annual['Cum Interest']
    bi_annual['PMI Saved'] = monthly_comp_annual['Cum PMI'] - bi_annual['Cum PMI']
    fig_saved_bi = px.line(bi_annual, x='Year', y=['Interest Saved', 'PMI Saved'], title=None, markers=True)
    fig_saved_bi.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        title_font_size=28, font=dict(family="Arial", size=14, color="black"),
        xaxis_title='Year',
        yaxis_title='Savings ($)'
    )
    st.plotly_chart(fig_saved_bi, use_container_width=True)

# General Inputs in main
st.subheader("Evaluation Period")
cols = st.columns(2)
eval_start_year = cols[0].number_input("Evaluation Start Year", value=2025, step=1, min_value=2000, max_value=2100, key='eval_start_year')
eval_end_year = cols[1].number_input("Evaluation End Year", value=2070, step=1, min_value=eval_start_year, max_value=2100, key='eval_end_year')
if eval_end_year > purchase_year + loan_years:
    st.warning(f"Note: Evaluation End Year ({eval_end_year}) is beyond the loan term ({purchase_year + loan_years}). Metrics will assume the mortgage is paid off, and costs will include ongoing expenses (taxes, insurance, etc.).")

# Global Slider for Asset and Cost Sections
eval_years = range(eval_start_year, eval_end_year + 1)
with st.container(border=True):
    st.markdown("<h3 style='margin: 0; text-align: center;'>Evaluation Year Selection</h3>", unsafe_allow_html=True)
    selected_year = st.slider("Select Evaluation Year for Assets and Costs", min_value=min(eval_years), max_value=max(eval_years), value=min(eval_years), help="Slide to change the year for which asset and cost metrics are calculated.", label_visibility="collapsed")

# Wealth Metrics Below Amortization
st.subheader("Wealth Metrics")
st.markdown(f"**Note**: Metrics are for the selected evaluation year ({selected_year}). Buying wealth includes home equity (home value minus loan balance), appreciation (increase in home value), and VTI investments (from cost savings when buying is cheaper). Renting wealth includes VTI investments (from cost savings when renting is cheaper).")

final_year = selected_year
final_data = cost_comparison_df[cost_comparison_df["Year"] == final_year]

if not final_data.empty:
    final_balance = main_annual_df[main_annual_df["Date"].dt.year == final_year]["Balance"].iloc[-1] if final_year in main_annual_df["Date"].dt.year.values else 0
    final_home_value = purchase_price * (1 + annual_appreciation / 100) ** (final_year - purchase_year)
    equity_gain = final_data["Equity Gain"].iloc[0]
    appreciation = final_data["Appreciation"].iloc[0]
    buying_investment = final_data["Buying Investment"].iloc[0]
    renting_investment = final_data["Renting Investment"].iloc[0]
    buying_assets = final_data["Buying Total Assets"].iloc[0]
    renting_assets = final_data["Renting Total Assets"].iloc[0]
    wealth_difference = buying_assets - renting_assets
else:
    # Fallback calculations
    year_idx = final_year - purchase_year
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
    wealth_difference = buying_assets - renting_assets

buy_col, rent_col = st.columns(2)
with buy_col:
    with st.container(border=True):
        st.markdown("#### Buying - Wealth Metrics (Selected Year)")
        buy_wealth_df = pd.DataFrame({
            "Item": ["Equity", "Appreciation", "Investment"],
            "Value": [equity_gain, appreciation, buying_investment]
        })
        buy_wealth_df = buy_wealth_df[buy_wealth_df["Value"] > 0]
        total_buy = buy_wealth_df["Value"].sum()
        buy_wealth_df["% of Total"] = (buy_wealth_df["Value"] / total_buy) * 100 if total_buy > 0 else 0
        total_buy_row = pd.DataFrame({"Item": ["Total"], "Value": [total_buy], "% of Total": [100.0]})
        buy_wealth_df = pd.concat([buy_wealth_df, total_buy_row], ignore_index=True)
        st.dataframe(buy_wealth_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"}), hide_index=True)

with rent_col:
    with st.container(border=True):
        st.markdown("#### Renting - Wealth Metrics (Selected Year)")
        rent_wealth_df = pd.DataFrame({
            "Item": ["Investment"],
            "Value": [renting_investment]
        })
        rent_wealth_df = rent_wealth_df[rent_wealth_df["Value"] > 0]
        total_rent = rent_wealth_df["Value"].sum()
        rent_wealth_df["% of Total"] = (rent_wealth_df["Value"] / total_rent) * 100 if total_rent > 0 else 0
        total_rent_row = pd.DataFrame({"Item": ["Total"], "Value": [total_rent], "% of Total": [100.0]})
        rent_wealth_df = pd.concat([rent_wealth_df, total_rent_row], ignore_index=True)
        st.dataframe(rent_wealth_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"}), hide_index=True)

with st.container(border=True):
    st.markdown("### Wealth Comparison")
    st.metric(f"Wealth Difference ({final_year}) (Buy - Rent)", f"${wealth_difference:,.2f}", delta_color="normal", help="Positive means buying yields more wealth; negative means renting yields more.")

# Wealth Treemap
wealth_treemap_data_selected = cost_comparison_df[cost_comparison_df['Year'] == selected_year].melt(
    id_vars=['Year'],
    value_vars=['Equity Gain', 'Appreciation', 'Buying Investment'],
    var_name='Category',
    value_name='Value'
)
wealth_treemap_data_selected = wealth_treemap_data_selected[wealth_treemap_data_selected['Value'] > 0]

rent_wealth_treemap_data_selected = cost_comparison_df[cost_comparison_df['Year'] == selected_year].melt(
    id_vars=['Year'],
    value_vars=['Renting Investment'],
    var_name='Category',
    value_name='Value'
)
rent_wealth_treemap_data_selected = rent_wealth_treemap_data_selected[rent_wealth_treemap_data_selected['Value'] > 0]

col1, col2 = st.columns(2)
with col1:
    fig_buy_wealth = px.treemap(wealth_treemap_data_selected, path=['Category'], values='Value', title=None)
    st.plotly_chart(fig_buy_wealth, use_container_width=True)
with col2:
    fig_rent_wealth = px.treemap(rent_wealth_treemap_data_selected, path=['Category'], values='Value', title=None)
    st.plotly_chart(fig_rent_wealth, use_container_width=True)

with st.expander("Detailed Wealth/Assets by Year", expanded=False):
    wealth_breakout = cost_comparison_df[['Year', 'Equity Gain', 'Appreciation', 'Buying Investment', 'Buying Total Assets', 'Renting Investment', 'Renting Total Assets', 'Asset Difference (Buy - Rent)']]
    wealth_breakout['Year'] = wealth_breakout['Year'].apply(lambda x: str(x))
    formatters = {col: "${:,.2f}" for col in wealth_breakout.columns if col != 'Year'}
    formatters['Year'] = "{}"
    st.dataframe(wealth_breakout.style.format(formatters), hide_index=True)

# Total Assets Over Time
st.subheader("Total Assets Over Time")
tab_abs, tab_perc = st.tabs(["Absolute", "% Difference"])
with tab_abs:
    asset_data = pd.concat([
        pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Assets": cost_comparison_df["Buying Total Assets"],
            "Type": "Buying"
        }),
        pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Assets": cost_comparison_df["Renting Total Assets"],
            "Type": "Renting"
        })
    ])

    fig_assets = px.line(asset_data, x='Year', y='Assets', color='Type', title=None, markers=True)
    fig_assets.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        title_font_size=28, font=dict(family="Arial", size=14, color="black"),
        legend_title_text="Type",
        xaxis_title='Year',
        yaxis_title='Total Assets ($)'
    )
    if show_refinance and refi_start_date:
        fig_assets.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    fig_assets.add_vline(x=purchase_year, line_dash="dash", line_color="purple", annotation_text="Purchase")
    if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
        fig_assets.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_assets, use_container_width=True)
with tab_perc:
    fig_perc_assets = px.line(cost_comparison_df, x='Year', y='Asset % Difference (Buy vs Rent)', title=None, markers=True)
    fig_perc_assets.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        title_font_size=28, font=dict(family="Arial", size=14, color="black"),
        xaxis_title='Year',
        yaxis_title='Percent Difference (%)'
    )
    fig_perc_assets.add_hline(y=0, line_dash="dash", line_color="black")
    if show_refinance and refi_start_date:
        fig_perc_assets.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    fig_perc_assets.add_vline(x=purchase_year, line_dash="dash", line_color="purple", annotation_text="Purchase")
    if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
        fig_perc_assets.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_perc_assets, use_container_width=True)

st.divider()

# Cost Comparison: Buy vs. Rent
st.subheader("Cost Metrics")
st.markdown("**Note**: Buying costs include Direct (P&I, principal payments, extra payments) and Indirect (PMI, Taxes, Insurance, Maintenance, Emergency, HOA, all Closing/Points if paid upfront). Financing Method indicates whether costs are 'Upfront' or 'Financed'. Renting includes Rent, Renters' Insurance, Deposits, Utilities, Pet Fees, Application/Renewal/Parking Fees. Down payment is not included as a cost but as initial equity in buying or invested in renting.")

buy_col, rent_col = st.columns(2)
with buy_col:
    with st.container(border=True):
        st.markdown("### Buy Costs")
        cols = st.columns(2)
        cols[0].metric(f"Total Cost ({final_year})", f"${final_data['Total Buying Cost'].iloc[0]:,.2f}")
with rent_col:
    with st.container(border=True):
        st.markdown("### Rent Costs")
        cols = st.columns(2)
        cols[0].metric(f"Total Cost ({final_year})", f"${final_data['Total Renting Cost'].iloc[0]:,.2f}")

# Treemap for Cost Breakdown at Selected Year
buy_treemap_data_selected = cost_comparison_df[cost_comparison_df['Year'] == selected_year].melt(
    id_vars=['Year'],
    value_vars=['Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs'],
    var_name='Category',
    value_name='Cost'
)
buy_treemap_data_selected = buy_treemap_data_selected[buy_treemap_data_selected['Cost'] > 0]

rent_treemap_data_selected = cost_comparison_df[cost_comparison_df['Year'] == selected_year].melt(
    id_vars=['Year'],
    value_vars=['Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee'],
    var_name='Category',
    value_name='Cost'
)
rent_treemap_data_selected = rent_treemap_data_selected[rent_treemap_data_selected['Cost'] > 0]

col1, col2 = st.columns(2)
with col1:
    fig_buy_cost = px.treemap(buy_treemap_data_selected, path=['Category'], values='Cost', title=None)
    st.plotly_chart(fig_buy_cost, use_container_width=True)
with col2:
    fig_rent_cost = px.treemap(rent_treemap_data_selected, path=['Category'], values='Cost', title=None)
    st.plotly_chart(fig_rent_cost, use_container_width=True)

# Associated Costs
st.markdown("### Associated Costs")
buy_cost_cols = ['Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs']
rent_cost_cols = ['Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee']

buy_cost_totals = cost_comparison_df[buy_cost_cols].mean().reset_index()
buy_cost_totals.columns = ['Category', 'Average Cost']
buy_cost_totals = buy_cost_totals[buy_cost_totals['Average Cost'] > 0].sort_values('Average Cost', ascending=False)
buy_total_avg = buy_cost_totals['Average Cost'].sum()
buy_cost_totals['% of Total'] = (buy_cost_totals['Average Cost'] / buy_total_avg) * 100
total_buy_row = pd.DataFrame({"Category": ["Total"], "Average Cost": [buy_total_avg], "% of Total": [100.0]})
buy_cost_totals = pd.concat([buy_cost_totals, total_buy_row], ignore_index=True)

rent_cost_totals = cost_comparison_df[rent_cost_cols].mean().reset_index()
rent_cost_totals.columns = ['Category', 'Average Cost']
rent_cost_totals = rent_cost_totals[rent_cost_totals['Average Cost'] > 0].sort_values('Average Cost', ascending=False)
rent_total_avg = rent_cost_totals['Average Cost'].sum()
rent_cost_totals['% of Total'] = (rent_cost_totals['Average Cost'] / rent_total_avg) * 100
total_rent_row = pd.DataFrame({"Category": ["Total"], "Average Cost": [rent_total_avg], "% of Total": [100.0]})
rent_cost_totals = pd.concat([rent_cost_totals, total_rent_row], ignore_index=True)

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("#### Buying - Associated Costs (Average Across Years)")
        st.dataframe(buy_cost_totals.style.format({"Average Cost": "${:,.2f}", "% of Total": "{:.2f}%"}), hide_index=True)
with col2:
    with st.container(border=True):
        st.markdown("#### Renting - Associated Costs (Average Across Years)")
        st.dataframe(rent_cost_totals.style.format({"Average Cost": "${:,.2f}", "% of Total": "{:.2f}%"}), hide_index=True)

st.subheader("Costs")
st.markdown("**Included Costs**: Buying: P&I (including principal and extra payments), PMI, taxes, insurance, maintenance, emergency, HOA, closing/points (if upfront). Renting: Rent, insurance, deposits, utilities, pet fees, application/renewal/parking. Down payment is invested in rent scenario or equity in buy.")
total_costs_data = pd.concat([
    pd.DataFrame({
        "Year": cost_comparison_df["Year"],
        "Cost": cost_comparison_df["Total Buying Cost"],
        "Cumulative Cost": cost_comparison_df["Cumulative Buying Cost"],
        "Type": "Buying"
    }),
    pd.DataFrame({
        "Year": cost_comparison_df["Year"],
        "Cost": cost_comparison_df["Total Renting Cost"],
        "Cumulative Cost": cost_comparison_df["Cumulative Renting Cost"],
        "Type": "Renting"
    })
])

tab1, tab2 = st.tabs(["Non-Cumulative", "Cumulative"])
with tab1:
    fig_non_cum = px.line(total_costs_data, x='Year', y='Cost', color='Type', title=None, markers=True)
    fig_non_cum.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        title_font_size=28, font=dict(family="Arial", size=14, color="black"),
        legend_title_text="Type",
        xaxis_title='Year',
        yaxis_title='Annual Cost ($)'
    )
    if show_refinance and refi_start_date:
        fig_non_cum.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    fig_non_cum.add_vline(x=purchase_year, line_dash="dash", line_color="purple", annotation_text="Purchase")
    if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
        fig_non_cum.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_non_cum, use_container_width=True)

with tab2:
    fig_cum = px.line(total_costs_data, x='Year', y='Cumulative Cost', color='Type', title=None, markers=True)
    fig_cum.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        title_font_size=28, font=dict(family="Arial", size=14, color="black"),
        legend_title_text="Type",
        xaxis_title='Year',
        yaxis_title='Cumulative Cost ($)'
    )
    if show_refinance and refi_start_date:
        fig_cum.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    fig_cum.add_vline(x=purchase_year, line_dash="dash", line_color="purple", annotation_text="Purchase")
    if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
        fig_cum.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_cum, use_container_width=True)

# Stacked Bar Chart for One-time vs Repeating Costs
st.subheader("One-time vs Repeating Costs")
cost_comparison_df['Buy One-time'] = cost_comparison_df['Closing Costs'] + cost_comparison_df['Points Costs'] + cost_comparison_df['Emergency']  # Assume emergency is one-time; adjust as needed
cost_comparison_df['Buy Repeating'] = cost_comparison_df['Total Buying Cost'] - cost_comparison_df['Buy One-time']
cost_comparison_df['Rent One-time'] = cost_comparison_df['Security Deposit'] + cost_comparison_df['Application Fee'] + (cost_comparison_df['Pet Fees'] if pet_fee_frequency == "One-time" else 0)
cost_comparison_df['Rent Repeating'] = cost_comparison_df['Total Renting Cost'] - cost_comparison_df['Rent One-time']

stacked_data = cost_comparison_df.melt(id_vars=['Year'], value_vars=['Buy One-time', 'Buy Repeating', 'Rent One-time', 'Rent Repeating'], var_name='Type', value_name='Cost')

fig_stacked = px.bar(stacked_data, x='Year', y='Cost', color='Type', title=None, barmode='stack')
fig_stacked.update_layout(xaxis_title='Year', yaxis_title='Cost ($)')
st.plotly_chart(fig_stacked, use_container_width=True)

with st.expander("Detailed Costs Breakdown by Year", expanded=False):
    costs_breakout = cost_comparison_df[['Year', 'Total Buying Cost', 'Total Renting Cost', 'Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs', 'Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee']]
    costs_breakout['Year'] = costs_breakout['Year'].apply(lambda x: str(x))
    formatters = {col: "${:,.2f}" for col in costs_breakout.columns if col != 'Year'}
    formatters['Year'] = "{}"
    st.dataframe(costs_breakout.style.format(formatters), hide_index=True)

# Combined Difference Visual
st.subheader("Difference Between Rent vs. Buy")
tab1, tab2 = st.tabs(["Absolute Asset Difference (Buy - Rent)", "% Difference in End Balances (Buy vs Rent)"])

with tab1:
    diff_data = cost_comparison_df[['Year', 'Asset Difference (Buy - Rent)']]
    fig_diff_abs = px.line(diff_data, x='Year', y='Asset Difference (Buy - Rent)', title=None, markers=True)
    fig_diff_abs.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        title_font_size=28, font=dict(family="Arial", size=14, color="black"),
        xaxis_title='Year',
        yaxis_title='Difference ($)'
    )
    fig_diff_abs.add_hline(y=0, line_dash="dash", line_color="black")
    if show_refinance and refi_start_date:
        fig_diff_abs.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    fig_diff_abs.add_vline(x=purchase_year, line_dash="dash", line_color="purple", annotation_text="Purchase")
    if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
        fig_diff_abs.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_diff_abs, use_container_width=True)

with tab2:
    diff_df_melt = cost_comparison_df.melt(
        id_vars="Year",
        value_vars=["Asset % Difference (Buy vs Rent)"],
        var_name="Comparison",
        value_name="Percent Difference"
    )

    fig_diff = px.line(
        diff_df_melt,
        x="Year",
        y="Percent Difference",
        color="Comparison",
        markers=True,
        title=None,
    )
    fig_diff.update_layout(
        plot_bgcolor="rgb(245, 245, 245)",
        paper_bgcolor="rgb(245, 245, 245)",
        title_font_size=28,
        font=dict(family="Arial", size=14, color="black"),
        legend_title_text="Comparison",
        xaxis_title='Year',
        yaxis_title='Percent Difference (%)'
    )
    fig_diff.add_hline(y=0, line_dash="dash", line_color="black")
    if show_refinance and refi_start_date:
        fig_diff.add_vline(x=refi_start_date.year, line_dash="dash", line_color="red", annotation_text="Refinance")
    fig_diff.add_vline(x=purchase_year, line_dash="dash", line_color="purple", annotation_text="Purchase")
    if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
        fig_diff.add_vline(x=payoff_year, line_dash="dash", line_color="green", annotation_text="Payoff")
    st.plotly_chart(fig_diff, use_container_width=True)

# Mortgage Balance Over Time
st.subheader("Mortgage Balance Over Time")
st.markdown("**Note**: Shows the loan balance over time for the selected payment frequency.")
chart_data = pd.DataFrame({
    "Date": main_schedule_df["Date"],
    "Balance": main_schedule_df["Balance"],
    "Schedule": payment_frequency
})
chart_data = chart_data[chart_data["Date"].dt.year <= eval_end_year]

fig_balance = px.line(chart_data, x='Date', y='Balance', color='Schedule', title=None, markers=True)
fig_balance.update_layout(
    plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
    title_font_size=28, font=dict(family="Arial", size=14, color="black"),
    legend_title_text="Schedule",
    xaxis_title='Date',
    yaxis_title='Balance ($)'
)
if show_refinance and refi_start_date:
    fig_balance.add_vline(x=refi_start_date, line_dash="dash", line_color="red", annotation_text="Refinance")
st.plotly_chart(fig_balance, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Developed by Eric Hubbard | [KnowTheCostFinancial.com](https://knowthecostfinancial.com)")