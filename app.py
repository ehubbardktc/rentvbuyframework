# ----------------------------- IMPORTS -----------------------------
import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import datetime, timedelta
import altair as alt

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
    - **Visualizations**: Line charts for costs and assets, stacked bar/area charts for cost breakdowns, breakeven analysis, interactive tables.

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
    - Investments: Cost differences (buying vs. renting) are invested in VTI (default 7% annual return).
    - Equity: Homeowners gain equity from appreciation and principal; renters invest savings in VTI.
    """)

# ----------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.image("images/EyesWideOpenLogo.png", use_container_width=False, width=300)
    st.markdown("Tool developed by Eric Hubbard")
    st.markdown("[KnowTheCostFinancial.com](https://knowthecostfinancial.com)")

    st.markdown("---")

    # Define defaults to avoid NameError
    purchase_year = 2025  # Default value
    loan_years = 30       # Default value

    # Purchase Details
    with st.expander("Purchase Details", expanded=True):
        purchase_year = st.number_input("Purchase Year", value=purchase_year, step=1, min_value=2000, max_value=2100)
        purchase_price = st.number_input("Purchase Price ($)", value=500_000, step=10_000, min_value=0)
        down_payment = st.number_input("Down Payment ($)", value=100_000, step=1_000, min_value=0, max_value=purchase_price)
        closing_costs = st.number_input("Closing Costs ($)", value=5000, step=500, min_value=0)
        closing_costs_method = st.radio("Closing Costs Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
        loan_amount = purchase_price - down_payment + (closing_costs if closing_costs_method == "Add to Loan Balance" else 0)
        percent_down = (down_payment / purchase_price * 100) if purchase_price > 0 else 0
        st.metric("Loan Amount", f"${loan_amount:,.0f}")
        st.metric("% Down Payment", f"{percent_down:.2f}%")

    # Loan Terms & Mortgage
    with st.expander("Loan Terms & Mortgage", expanded=True):
        loan_years = st.number_input("Loan Length (Years)", value=loan_years, step=1, min_value=1, max_value=50)
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.01, min_value=0.0, format="%.3f")
        pmi_rate = st.number_input("PMI Rate (%)", value=0.20, step=0.01, min_value=0.0)
        pmi_equity_threshold = st.number_input("PMI Paid Until Equity (%)", value=20, step=1, min_value=0, max_value=100)
        payment_frequency = st.radio("Payment Frequency", ["Monthly", "Biweekly"], index=0)
        mortgage_type = st.radio("Mortgage Type", ["Fixed", "Variable"], index=0)

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
            points_cost_method = st.radio("Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
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

    # General Inputs
    with st.expander("General Inputs", expanded=True):
        eval_start_year = st.number_input("Evaluation Start Year", value=2025, step=1, min_value=2000, max_value=2100)
        eval_end_year = st.number_input("Evaluation End Year", value=2070, step=1, min_value=eval_start_year, max_value=2100)
        if eval_end_year > purchase_year + loan_years:
            st.warning(f"Note: Evaluation End Year ({eval_end_year}) is beyond the loan term ({purchase_year + loan_years}). Metrics will assume the mortgage is paid off, and costs will include ongoing expenses (taxes, insurance, etc.).")

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
            roll_costs = st.radio("Refinance Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
            refi_payment_frequency = st.radio("Refinance Payment Frequency", ["Monthly", "Biweekly"], index=0)
            refi_mortgage_type = st.radio("Refinance Mortgage Type", ["Fixed", "Variable"], index=0)
            refi_periods_per_year = 12 if refi_payment_frequency == "Monthly" else 26
            refi_effective_rate = refi_rate

            refi_buy_points = st.checkbox("Buy Points for Refinance?", value=False)
            if refi_buy_points:
                refi_points = st.number_input("Refinance Points", value=1.0, step=0.25, min_value=0.0)
                refi_discount_per_point = st.number_input("Refinance Rate Discount per Point (%)", value=0.25, step=0.01, min_value=0.0)
                refi_points_cost_method = st.radio("Refinance Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
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

    # Ongoing Expenses
    with st.expander("Ongoing Expenses", expanded=False):
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

    # Appreciation & Growth
    with st.expander("Appreciation & Growth", expanded=False):
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=3.5, step=0.1, min_value=0.0)
        annual_maintenance_increase = st.number_input("Annual Maintenance Increase (%)", value=3.0, step=0.1, min_value=0.0)
        annual_insurance_increase = st.number_input("Annual Insurance Increase (%)", value=3.0, step=0.1, min_value=0.0)
        annual_hoa_increase = st.number_input("Annual HOA Increase (%)", value=3.0, step=0.1, min_value=0.0)
        vti_annual_return = st.number_input("Annual VTI Return (%)", value=7.0, step=0.1, min_value=0.0, help="Annual return rate for investments in a low-cost index fund (e.g., VTI).")

    # Rental Assumptions
    with st.expander("Rental Assumptions", expanded=False):
        cost_of_rent = st.number_input("Initial Monthly Rent ($)", value=3000, step=50, min_value=0)
        annual_rent_increase = st.number_input("Annual Rent Increase (%)", value=4.0, step=0.1, min_value=0.0)
        renters_insurance = st.number_input("Annual Renters' Insurance ($)", value=300, step=50, min_value=0)
        security_deposit = st.number_input("Security Deposit ($)", value=3000, step=100, min_value=0)
        annual_deposit_increase = st.number_input("Annual Deposit Increase (%)", value=4.0, step=0.1, min_value=0.0)
        rental_utilities = st.number_input("Annual Rental Utilities ($)", value=2400, step=100, min_value=0)
        pet_fee = st.number_input("Pet Fee/Deposit ($)", value=500, step=50, min_value=0)
        pet_fee_frequency = st.radio("Pet Fee Frequency", ["One-time", "Annual"], index=0)
        application_fee = st.number_input("Application Fee ($)", value=50, step=10, min_value=0)
        lease_renewal_fee = st.number_input("Annual Lease Renewal Fee ($)", value=200, step=50, min_value=0)
        parking_fee = st.number_input("Monthly Parking Fee ($)", value=100, step=10, min_value=0)

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
    vti_annual_return=7.0
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
    rent_investment = 0

    for year in years:
        year_idx = year - purchase_year
        # Only include P&I and PMI if year is within loan term and mortgage is not paid off
        if year <= purchase_year + loan_years and year in annual_df["Date"].dt.year.values:
            p_and_i = annual_df[annual_df["Date"].dt.year == year]["Payment"].sum() + annual_df[annual_df["Date"].dt.year == year]["Extra"].sum()
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
            "Renting Total Assets": rent_total_assets
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
monthly_comparison_df, monthly_comparison_monthly_df, _ = amortization_schedule(
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

# Biweekly comparison schedule (for monthly main schedule)
biweekly_schedule_df, _, _ = amortization_schedule(
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

# Main Metrics
monthly_payment = main_schedule_df['Payment'].iloc[0] if main_periods_per_year == 12 else main_schedule_df['Payment'].iloc[0] * 26 / 12
payment_per_period = main_schedule_df['Payment'].iloc[0]
total_interest = main_schedule_df['Interest'].sum()
total_pmi = main_schedule_df['PMI'].sum()
payoff_years = len(main_schedule_df) / main_periods_per_year

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
    vti_annual_return=7.0
)

# Calculate Payoff Year
payoff_year = main_annual_df[main_annual_df["Balance"] <= 0]["Date"].dt.year.min() if (main_annual_df["Balance"] <= 0).any() else None

# ----------------------------- DISPLAY -----------------------------
st.subheader("Mortgage Metrics")
with st.container(border=True):
    st.markdown("### Main Scenario" + (" (with Refinance)" if show_refinance else " (Original Loan)") + f" ({payment_frequency} Payments)")
    cols = st.columns(5)
    cols[0].metric("Monthly Payment", f"${monthly_payment:,.2f}")
    cols[1].metric("Payment per Period", f"${payment_per_period:,.2f}")
    cols[2].metric("Total Interest", f"${total_interest:,.2f}")
    cols[3].metric("Total PMI", f"${total_pmi:,.2f}")
    cols[4].metric("Payoff Years", f"{payoff_years:.1f}")

if show_refinance and refi_start_date:
    st.subheader("Refinance Savings and Breakeven")
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
    st.subheader("Biweekly Savings (Compared to Monthly)")
    with st.container(border=True):
        cols = st.columns(2)
        if interest_saved_biweekly >= 0:
            cols[0].metric("Interest Saved", f"${interest_saved_biweekly:,.2f}")
        else:
            cols[0].metric("Additional Interest", f"${abs(interest_saved_biweekly):,.2f}")
        cols[1].metric("Payoff Time Difference", f"{abs(payoff_difference_biweekly):,.1f} years {'shorter' if payoff_difference_biweekly >= 0 else 'longer'}")

st.subheader("Equity and Wealth Metrics")
with st.container(border=True):
    st.markdown(f"**Note**: Metrics are for the final evaluation year ({eval_end_year}). Buying wealth includes home equity (home value minus loan balance), appreciation (increase in home value), and VTI investments (from cost savings when buying is cheaper). Renting wealth includes VTI investments (from cost savings when renting is cheaper).")
    final_year = eval_end_year
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

    # Display metrics side-by-side
    cols = st.columns(7)
    cols[0].metric(f"Buying Wealth ({final_year})", f"${buying_assets:,.2f}", help=f"Home equity plus VTI investments (at {vti_annual_return}% annual return).")
    cols[1].metric(f"Equity ({final_year})", f"${equity_gain:,.2f}", help=f"Home value (${final_home_value:,.2f}) minus loan balance (${final_balance:,.2f}).")
    cols[2].metric(f"Appreciation ({final_year})", f"${appreciation:,.2f}", help=f"Increase in home value at {annual_appreciation}% annual return.")
    cols[3].metric(f"Buying Investment ({final_year})", f"${buying_investment:,.2f}", help=f"VTI investments from cost savings at {vti_annual_return}% annual return.")
    cols[4].metric(f"Renting Wealth ({final_year})", f"${renting_assets:,.2f}", help=f"VTI investments from cost savings (at {vti_annual_return}% annual return).")
    cols[5].metric(f"Renting Investment ({final_year})", f"${renting_investment:,.2f}", help=f"VTI investments from cost savings at {vti_annual_return}% annual return.")
    cols[6].metric(f"Wealth Difference ({final_year})", f"${wealth_difference:,.2f}", delta_color="normal", help="Positive means buying yields more wealth; negative means renting yields more.")

st.subheader("Amortization Schedule")
st.markdown("**Note**: 'Loan Type' column indicates 'Original' or 'Refinance' (highlighted in blue). 'Effective Rate (%)' shows the interest rate applied, reflecting points or variable rates.")
tab1, tab2, tab3, tab4 = st.tabs(["Annual", "Monthly", "Balance Over Time", "Payment Frequency Comparison"])

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
        }).apply(lambda row: ["background-color: #e6f3ff; font-weight: bold" if row["Loan Type"] == "Refinance" else "font-weight: bold" if row.name == "Loan Type" else ""] * len(row), axis=1)
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
        }).apply(lambda row: ["background-color: #ffe699" if row["Num Payments"] > 1 else "background-color: #e6f3ff; font-weight: bold" if row["Loan Type"] == "Refinance" else "font-weight: bold" if row.name == "Loan Type" else ""] * len(row), axis=1)
    )

with tab3:
    st.subheader("Balance Over Time")
    chart_data = pd.DataFrame({
        "Date": main_schedule_df["Date"],
        "Balance": main_schedule_df["Balance"],
        "Schedule": "Main (with Refinance)" if show_refinance else "Main (Original)"
    })
    if show_refinance and refi_start_date:
        no_refi_chart_data = pd.DataFrame({
            "Date": no_refi_schedule_df["Date"],
            "Balance": no_refi_schedule_df["Balance"],
            "Schedule": "Original (No Refinance)"
        })
        chart_data = pd.concat([chart_data, no_refi_chart_data])

    chart_data = chart_data[chart_data["Date"].dt.year <= eval_end_year]

    line = alt.Chart(chart_data).mark_line().encode(
        x='Date:T',
        y=alt.Y('Balance:Q', title='Balance ($)'),
        color=alt.Color('Schedule:N', legend=alt.Legend(title="Schedule")),
        strokeDash=alt.condition(
            alt.datum.Schedule == "Original (No Refinance)",
            alt.value([5, 5]),
            alt.value([0])
        ),
        tooltip=['Date', alt.Tooltip('Balance:Q', format='$,.2f'), 'Schedule']
    ).interactive()

    if show_refinance and refi_start_date:
        vline = alt.Chart(pd.DataFrame({'Date': [refi_start_date]})).mark_rule(color='red', strokeDash=[5,5]).encode(
            x='Date:T',
            tooltip=['Date']
        )
        chart = line + vline
    else:
        chart = line

    st.altair_chart(chart, use_container_width=True)

with tab4:
    st.subheader("Payment Frequency Comparison")
    main_label = f"Main ({payment_frequency})"
    chart_data = pd.DataFrame({
        "Date": main_schedule_df["Date"],
        "Balance": main_schedule_df["Balance"],
        "Schedule": main_label
    })
    comparison_df = biweekly_schedule_df if payment_frequency == "Monthly" else monthly_comparison_df
    comparison_label = "Biweekly Comparison" if payment_frequency == "Monthly" else "Monthly Comparison"
    comparison_chart_data = pd.DataFrame({
        "Date": comparison_df["Date"],
        "Balance": comparison_df["Balance"],
        "Schedule": comparison_label
    })
    chart_data = pd.concat([chart_data, comparison_chart_data])

    chart_data = chart_data[chart_data["Date"].dt.year <= eval_end_year]

    line = alt.Chart(chart_data).mark_line().encode(
        x='Date:T',
        y=alt.Y('Balance:Q', title='Balance ($)'),
        color=alt.Color('Schedule:N', legend=alt.Legend(title="Schedule")),
        strokeDash=alt.condition(
            alt.datum.Schedule == comparison_label,
            alt.value([5, 5]),
            alt.value([0])
        ),
        tooltip=['Date', alt.Tooltip('Balance:Q', format='$,.2f'), 'Schedule']
    ).interactive()

    st.altair_chart(line, use_container_width=True)

# Cost Comparison and Visualizations
st.subheader("Cost Comparison: Buy vs. Rent")
st.markdown("**Note**: Buying costs include Direct (P&I) and Indirect (PMI, Taxes, Insurance, Maintenance, Emergency, HOA, all Closing/Points). Financing Method indicates whether costs are 'Upfront' or 'Financed'. Renting includes Rent, Renters' Insurance, Deposits, Utilities, Pet Fees, Application/Renewal/Parking Fees.")

# Add Rent Cost Components to cost_comparison_df
cost_comparison_df["Rent"] = cost_comparison_df["Year"].apply(lambda y: cost_of_rent * 12 * (1 + annual_rent_increase / 100) ** (y - purchase_year))
cost_comparison_df["Renters Insurance"] = cost_comparison_df["Year"].apply(lambda y: renters_insurance * (1 + annual_rent_increase / 100) ** (y - purchase_year))
cost_comparison_df["Security Deposit"] = cost_comparison_df["Year"].apply(lambda y: security_deposit * (1 + annual_deposit_increase / 100) ** (y - purchase_year) if y == purchase_year else 0)
cost_comparison_df["Utilities"] = cost_comparison_df["Year"].apply(lambda y: rental_utilities * (1 + annual_rent_increase / 100) ** (y - purchase_year))
cost_comparison_df["Pet Fees"] = cost_comparison_df["Year"].apply(lambda y: pet_fee * (1 + annual_deposit_increase / 100) ** (y - purchase_year) if pet_fee_frequency == "Annual" or (pet_fee_frequency == "One-time" and y == purchase_year) else 0)
cost_comparison_df["Application Fee"] = cost_comparison_df["Year"].apply(lambda y: application_fee if y == purchase_year else 0)
cost_comparison_df["Lease Renewal Fee"] = cost_comparison_df["Year"].apply(lambda y: lease_renewal_fee if y > purchase_year else 0)
cost_comparison_df["Parking Fee"] = cost_comparison_df["Year"].apply(lambda y: parking_fee * 12 * (1 + annual_rent_increase / 100) ** (y - purchase_year))

# Stacked Bar Charts for Cost Breakdown
buy_stack_data = cost_comparison_df.melt(
    id_vars=['Year'],
    value_vars=['Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs'],
    var_name='Category',
    value_name='Cost'
)
buy_stack_data = buy_stack_data[buy_stack_data['Cost'] > 0]

rent_stack_data = cost_comparison_df.melt(
    id_vars=['Year'],
    value_vars=['Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee'],
    var_name='Category',
    value_name='Cost'
)
rent_stack_data = rent_stack_data[rent_stack_data['Cost'] > 0]

buy_bar = alt.Chart(buy_stack_data).mark_bar().encode(
    x=alt.X('Year:O', title='Year', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Cost:Q', stack='zero', title='Annual Cost ($)'),
    color=alt.Color('Category:N', legend=alt.Legend(title="Buying Costs"), scale=alt.Scale(scheme='blues')),
    tooltip=['Year', 'Category', alt.Tooltip('Cost:Q', format='$,.2f')]
).properties(
    title="Buying Cost Breakdown Over Time",
    width=400,
    height=400
)

rent_bar = alt.Chart(rent_stack_data).mark_bar().encode(
    x=alt.X('Year:O', title='Year', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Cost:Q', stack='zero', title='Annual Cost ($)'),
    color=alt.Color('Category:N', legend=alt.Legend(title="Renting Costs"), scale=alt.Scale(scheme='greens')),
    tooltip=['Year', 'Category', alt.Tooltip('Cost:Q', format='$,.2f')]
).properties(
    title="Renting Cost Breakdown Over Time",
    width=400,
    height=400
)

st.altair_chart(alt.hconcat(buy_bar, rent_bar), use_container_width=True)

st.dataframe(
    cost_comparison_df.style.format({
        "Direct Costs (P&I)": "${:,.2f}",
        "Indirect Costs": "${:,.2f}",
        "PMI": "${:,.2f}",
        "Property Taxes": "${:,.2f}",
        "Home Insurance": "${:,.2f}",
        "Maintenance": "${:,.2f}",
        "Emergency": "${:,.2f}",
        "HOA Fees": "${:,.2f}",
        "Closing Costs": "${:,.2f}",
        "Points Costs": "${:,.2f}",
        "Total Buying Cost": "${:,.2f}",
        "Total Renting Cost": "${:,.2f}",
        "Cumulative Buying Cost": "${:,.2f}",
        "Cumulative Renting Cost": "${:,.2f}",
        "Cost Difference (Buy - Rent)": "${:,.2f}",
        "Equity Gain": "${:,.2f}",
        "Appreciation": "${:,.2f}",
        "Buying Investment": "${:,.2f}",
        "Renting Investment": "${:,.2f}",
        "Buying Total Assets": "${:,.2f}",
        "Renting Total Assets": "${:,.2f}",
        "Rent": "${:,.2f}",
        "Renters Insurance": "${:,.2f}",
        "Security Deposit": "${:,.2f}",
        "Utilities": "${:,.2f}",
        "Pet Fees": "${:,.2f}",
        "Application Fee": "${:,.2f}",
        "Lease Renewal Fee": "${:,.2f}",
        "Parking Fee": "${:,.2f}"
    })
)

# Total Costs Line Chart
st.subheader("Total Costs Over Time")
total_costs_data = pd.concat([
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
line_chart = alt.Chart(total_costs_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Year', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Cost:Q', title='Cumulative Cost ($)'),
    color=alt.Color('Type:N', legend=alt.Legend(title="Cost Type", orient='top-left'), scale=alt.Scale(domain=['Buying', 'Renting'], range=['#1f77b4', '#2ca02c'])),
    tooltip=['Year', alt.Tooltip('Cost:Q', format='$,.2f'), 'Type']
).interactive()

area_chart = alt.Chart(total_costs_data).mark_area(opacity=0.2).encode(
    x=alt.X('Year:O', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Cost:Q', stack=None),
    color=alt.Color('Type:N', scale=alt.Scale(domain=['Buying', 'Renting'], range=['#1f77b4', '#2ca02c']))
)

vlines = []
if show_refinance and refi_start_date:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [refi_start_date.year]})).mark_rule(color='red', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Refinance Year')]
    ))
vlines.append(alt.Chart(pd.DataFrame({'Year': [purchase_year]})).mark_rule(color='purple', strokeDash=[5,5]).encode(
    x='Year:O',
    tooltip=['Year', alt.Tooltip('Year:O', title='Purchase Year')]
))
if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [payoff_year]})).mark_rule(color='green', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Payoff Year')]
    ))

chart = alt.layer(area_chart, line_chart, *vlines).configure_axis(
    labelAngle=45
).properties(
    title="Cumulative Buying vs. Renting Costs",
    width=800,
    height=400
)

st.altair_chart(chart, use_container_width=True)

# Cost Difference Line Chart
st.subheader("Cost Difference (Buying - Renting)")
difference_data = cost_comparison_df[['Year', 'Cost Difference (Buy - Rent)', 'Cumulative Buying Cost', 'Cumulative Renting Cost']].copy()
difference_data['Color'] = difference_data['Cost Difference (Buy - Rent)'].apply(lambda x: '#ff7f0e' if x > 0 else '#2ca02c')
difference_chart = alt.Chart(difference_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Year', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Cost Difference (Buy - Rent):Q', title='Cost Difference ($)'),
    color=alt.Color('Color:N', scale=None),
    tooltip=['Year', alt.Tooltip('Cost Difference (Buy - Rent):Q', format='$,.2f'), alt.Tooltip('Cumulative Buying Cost:Q', format='$,.2f'), alt.Tooltip('Cumulative Renting Cost:Q', format='$,.2f')]
).interactive()

area_chart = alt.Chart(difference_data).mark_area(opacity=0.3).encode(
    x=alt.X('Year:O', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Cost Difference (Buy - Rent):Q'),
    color=alt.Color('Color:N', scale=None)
)

zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='black', strokeDash=[3,3]).encode(
    y='y:Q'
)

vlines = []
if show_refinance and refi_start_date:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [refi_start_date.year]})).mark_rule(color='red', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Refinance Year')]
    ))
if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [payoff_year]})).mark_rule(color='green', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Payoff Year')]
    ))

chart = alt.layer(area_chart, difference_chart, zero_line, *vlines).configure_axis(
    labelAngle=45
).properties(
    title="Cost Difference (Buying - Renting) Over Time",
    width=800,
    height=400
)

st.altair_chart(chart, use_container_width=True)

# Asset Comparison Chart
st.subheader("Asset Comparison: Buying vs. Renting")
st.markdown(f"**Note**: Buying assets include home equity (home value minus loan balance) plus investments in a low-cost index fund (VTI) from cost savings when buying is cheaper. Renting assets include investments in VTI from cost savings when renting is cheaper, assuming {vti_annual_return}% annual return.")

asset_data = pd.concat([
    pd.DataFrame({
        "Year": cost_comparison_df["Year"],
        "Assets": cost_comparison_df["Buying Total Assets"],
        "Type": "Buying (Equity + Investment)"
    }),
    pd.DataFrame({
        "Year": cost_comparison_df["Year"],
        "Assets": cost_comparison_df["Renting Total Assets"],
        "Type": "Renting (Investment)"
    })
])
asset_chart = alt.Chart(asset_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Year', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Assets:Q', title='Total Assets ($)'),
    color=alt.Color('Type:N', legend=alt.Legend(title="Asset Type", orient='top-left'), scale=alt.Scale(domain=['Buying (Equity + Investment)', 'Renting (Investment)'], range=['#1f77b4', '#2ca02c'])),
    tooltip=['Year', alt.Tooltip('Assets:Q', format='$,.2f'), 'Type']
).interactive()

area_chart = alt.Chart(asset_data).mark_area(opacity=0.2).encode(
    x=alt.X('Year:O', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Assets:Q', stack=None),
    color=alt.Color('Type:N', scale=alt.Scale(domain=['Buying (Equity + Investment)', 'Renting (Investment)'], range=['#1f77b4', '#2ca02c']))
)

equity_chart = alt.Chart(cost_comparison_df).mark_line(strokeDash=[5,5], color='#ff7f0e').encode(
    x=alt.X('Year:O', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Equity Gain:Q', title='Equity Gain ($)', axis=alt.Axis(titleColor='#ff7f0e')),
    tooltip=['Year', alt.Tooltip('Equity Gain:Q', format='$,.2f')]
).interactive()

vlines = []
if show_refinance and refi_start_date:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [refi_start_date.year]})).mark_rule(color='red', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Refinance Year')]
    ))
vlines.append(alt.Chart(pd.DataFrame({'Year': [purchase_year]})).mark_rule(color='purple', strokeDash=[5,5]).encode(
    x='Year:O',
    tooltip=['Year', alt.Tooltip('Year:O', title='Purchase Year')]
))
if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [payoff_year]})).mark_rule(color='green', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Payoff Year')]
    ))

chart = alt.layer(area_chart, asset_chart, equity_chart, *vlines).configure_axis(
    labelAngle=45
).properties(
    title="Buying vs. Renting Assets Over Time",
    width=800,
    height=400
)

st.altair_chart(chart, use_container_width=True)

# Asset Composition Over Time
st.subheader("Asset Composition Over Time")
st.markdown(f"**Note**: This chart breaks down the components of total assets for both buying and renting scenarios. For buying, it includes Equity Gain (home value minus loan balance), Appreciation (increase in home value, shown in orange), and Buying Investment (VTI investments from cost savings when buying is cheaper). For renting, it includes Renting Investment (VTI investments from cost savings when renting is cheaper). All investments assume a {vti_annual_return}% annual return.")

asset_composition_data = cost_comparison_df.melt(
    id_vars=['Year'],
    value_vars=['Equity Gain', 'Appreciation', 'Buying Investment', 'Renting Investment'],
    var_name='Category',
    value_name='Amount'
)
asset_composition_data = asset_composition_data[asset_composition_data['Amount'] > 0]

color_scale = alt.Scale(
    domain=['Equity Gain', 'Appreciation', 'Buying Investment', 'Renting Investment'],
    range=['#1f77b4', '#ff7f0e', '#aec7e8', '#2ca02c']
)

stacked_area = alt.Chart(asset_composition_data).mark_area().encode(
    x=alt.X('Year:O', title='Year', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Amount:Q', stack='zero', title='Asset Amount ($)'),
    color=alt.Color('Category:N', legend=alt.Legend(title="Asset Category"), scale=color_scale),
    tooltip=['Year', 'Category', alt.Tooltip('Amount:Q', format='$,.2f')]
).interactive()

vlines = []
if show_refinance and refi_start_date:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [refi_start_date.year]})).mark_rule(color='red', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Refinance Year')]
    ))
vlines.append(alt.Chart(pd.DataFrame({'Year': [purchase_year]})).mark_rule(color='purple', strokeDash=[5,5]).encode(
    x='Year:O',
    tooltip=['Year', alt.Tooltip('Year:O', title='Purchase Year')]
))
if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [payoff_year]})).mark_rule(color='green', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Payoff Year')]
    ))

chart = alt.layer(stacked_area, *vlines).configure_axis(
    labelAngle=45
).properties(
    title="Asset Composition Over Time",
    width=800,
    height=400
)

st.altair_chart(chart, use_container_width=True)

# Wealth Breakeven Point Chart
st.subheader("Wealth Breakeven Analysis")
st.markdown("**Note**: This chart shows when the total assets from buying (equity + investments) surpass renting (investments only). The breakeven point is marked with a vertical line where buying wealth exceeds renting wealth.")

# Prepare data
breakeven_data = cost_comparison_df[['Year', 'Buying Total Assets', 'Renting Total Assets']].copy()
breakeven_data['Wealth Difference'] = breakeven_data['Buying Total Assets'] - breakeven_data['Renting Total Assets']
breakeven_data['Color'] = breakeven_data['Wealth Difference'].apply(lambda x: '#1f77b4' if x >= 0 else '#2ca02c')

# Find breakeven year (first year where Buying Total Assets >= Renting Total Assets)
breakeven_year = breakeven_data[breakeven_data['Wealth Difference'] >= 0]['Year'].min() if (breakeven_data['Wealth Difference'] >= 0).any() else None

# Line chart for wealth difference
wealth_diff_chart = alt.Chart(breakeven_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Year', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Wealth Difference:Q', title='Wealth Difference (Buying - Renting) ($)'),
    color=alt.Color('Color:N', scale=None),
    tooltip=['Year', alt.Tooltip('Wealth Difference:Q', format='$,.2f'), alt.Tooltip('Buying Total Assets:Q', format='$,.2f'), alt.Tooltip('Renting Total Assets:Q', format='$,.2f')]
).interactive()

# Area chart for visual effect
area_chart = alt.Chart(breakeven_data).mark_area(opacity=0.3).encode(
    x=alt.X('Year:O', scale=alt.Scale(domain=list(range(eval_start_year, eval_end_year + 1)))),
    y=alt.Y('Wealth Difference:Q'),
    color=alt.Color('Color:N', scale=None)
)

# Zero line
zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='black', strokeDash=[3,3]).encode(
    y='y:Q'
)

# Breakeven line and annotation
vlines = []
annotations = []
if breakeven_year is not None and eval_start_year <= breakeven_year <= eval_end_year:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [breakeven_year]})).mark_rule(color='purple', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Breakeven Year')]
    ))
    annotations.append(alt.Chart(pd.DataFrame({'Year': [breakeven_year], 'Text': ['Breakeven']})).mark_text(
        align='left', dx=5, dy=-10, fontSize=12, fontWeight='bold', color='purple'
    ).encode(
        x='Year:O',
        y=alt.value(0),
        text='Text:N'
    ))

# Combine existing vertical lines
if show_refinance and refi_start_date:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [refi_start_date.year]})).mark_rule(color='red', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Refinance Year')]
    ))
if payoff_year is not None and eval_start_year <= payoff_year <= eval_end_year:
    vlines.append(alt.Chart(pd.DataFrame({'Year': [payoff_year]})).mark_rule(color='green', strokeDash=[5,5]).encode(
        x='Year:O',
        tooltip=['Year', alt.Tooltip('Year:O', title='Payoff Year')]
    ))

chart = alt.layer(area_chart, wealth_diff_chart, zero_line, *vlines, *annotations).configure_axis(
    labelAngle=45
).properties(
    title="Wealth Breakeven: Buying vs. Renting",
    width=800,
    height=400
)

st.altair_chart(chart, use_container_width=True)

# Interactive Sankey Diagram for Cost Flows (simulated with stacked bars)
st.subheader("Cost Flow Analysis (Sankey Style)")
st.markdown("**Note**: Select a year to visualize how costs are distributed for buying and renting. Buying costs flow into mortgage payments, taxes, insurance, etc., while renting costs flow into rent, utilities, fees, etc.")

# Year selector
selected_year = st.slider("Select Year for Cost Flow", min_value=int(eval_start_year), max_value=int(eval_end_year), value=int(purchase_year))

# Prepare data for selected year
buy_flow_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][[
    'Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 
    'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs'
]].melt(var_name='Category', value_name='Amount')
buy_flow_data['Type'] = 'Buying'
buy_flow_data = buy_flow_data[buy_flow_data['Amount'] > 0]

rent_flow_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][[
    'Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 
    'Application Fee', 'Lease Renewal Fee', 'Parking Fee'
]].melt(var_name='Category', value_name='Amount')
rent_flow_data['Type'] = 'Renting'
rent_flow_data = rent_flow_data[rent_flow_data['Amount'] > 0]

flow_data = pd.concat([buy_flow_data, rent_flow_data])

# Stacked bar to mimic Sankey flow
flow_chart = alt.Chart(flow_data).mark_bar().encode(
    x=alt.X('Type:N', title=None, axis=None),
    y=alt.Y('Amount:Q', stack='normalize', title='Cost Distribution', axis=alt.Axis(format='%')),
    color=alt.Color('Category:N', legend=alt.Legend(title="Cost Category"), scale=alt.Scale(scheme='tableau20')),
    tooltip=['Type', 'Category', alt.Tooltip('Amount:Q', format='$,.2f')]
).properties(
    title=f"Cost Flow for Year {selected_year}",
    width=400,
    height=400
).facet(
    column=alt.Column('Type:N', title=None)
).resolve_scale(
    y='shared'
)

st.altair_chart(flow_chart, use_container_width=True)

# Animated Asset Growth Donut Chart
st.subheader("Asset Composition Donut Chart")
st.markdown("**Note**: Select a year to see the proportion of assets for buying (equity vs. investment) and renting (investment only). The chart updates dynamically to show how asset composition changes over time.")

# Year selector
selected_year = st.slider("Select Year for Asset Composition", min_value=int(eval_start_year), max_value=int(eval_end_year), value=int(purchase_year))

# Prepare data for selected year
asset_donut_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][[
    'Equity Gain', 'Buying Investment', 'Renting Investment'
]].melt(var_name='Category', value_name='Amount')
asset_donut_data['Type'] = asset_donut_data['Category'].map({
    'Equity Gain': 'Buying',
    'Buying Investment': 'Buying',
    'Renting Investment': 'Renting'
})
asset_donut_data = asset_donut_data[asset_donut_data['Amount'] > 0]

# Donut chart
donut_chart = alt.Chart(asset_donut_data).mark_arc(innerRadius=50).encode(
    theta=alt.Theta('Amount:Q', stack=True),
    color=alt.Color('Category:N', legend=alt.Legend(title="Asset Category"), scale=alt.Scale(domain=['Equity Gain', 'Buying Investment', 'Renting Investment'], range=['#1f77b4', '#aec7e8', '#2ca02c'])),
    tooltip=['Type', 'Category', alt.Tooltip('Amount:Q', format='$,.2f')]
).properties(
    title=f"Asset Composition for Year {selected_year}",
    width=400,
    height=400
).facet(
    column=alt.Column('Type:N', title=None)
)

st.altair_chart(donut_chart, use_container_width=True)

# Scenario Comparison Heatmap
st.subheader("Scenario Analysis: Wealth Difference Heatmap")
st.markdown("**Note**: This heatmap shows the wealth difference (Buying - Renting) in the final evaluation year for different housing appreciation and VTI return rates. Blue indicates buying is more advantageous; green indicates renting.")

# Input ranges
appreciation_rates = st.slider("Select Housing Appreciation Rates (%)", min_value=0.0, max_value=10.0, value=(2.0, 5.0), step=0.5)
vti_rates = st.slider("Select VTI Annual Return Rates (%)", min_value=0.0, max_value=12.0, value=(5.0, 9.0), step=0.5)

# Generate scenario data
appreciation_steps = np.arange(appreciation_rates[0], appreciation_rates[1] + 0.5, 0.5)
vti_steps = np.arange(vti_rates[0], vti_rates[1] + 0.5, 0.5)
scenario_data = []

for appr in appreciation_steps:
    for vti in vti_steps:
        temp_df = calculate_cost_comparison(
            main_annual_df, 
            edited_property_expenses, 
            edited_emergency_expenses, 
            purchase_year, 
            eval_start_year, 
            eval_end_year, 
            annual_appreciation=appr,
            annual_insurance_increase=annual_insurance_increase,
            annual_maintenance_increase=annual_maintenance_increase,
            annual_hoa_increase=annual_hoa_increase,
            cost_of_rent=cost_of_rent,
            annual_rent_increase=annual_rent_increase,
            renters_insurance=renters_insurance,
            annual_deposit_increase=annual_deposit_increase,
            security_deposit=security_deposit,
            points_cost=points_cost,
            points_cost_method=points_cost_method,
            closing_costs=closing_costs,
            closing_costs_method=closing_costs_method,
            refi_costs=refi_costs,
            roll_costs=roll_costs,
            refi_points_cost=refi_points_cost,
            refi_points_cost_method=refi_points_cost_method,
            rental_utilities=rental_utilities,
            pet_fee=pet_fee,
            pet_fee_frequency=pet_fee_frequency,
            application_fee=application_fee,
            lease_renewal_fee=lease_renewal_fee,
            parking_fee=parking_fee,
            purchase_price=purchase_price,
            vti_annual_return=vti
        )
        final_wealth_diff = temp_df[temp_df['Year'] == eval_end_year]['Buying Total Assets'].iloc[0] - temp_df[temp_df['Year'] == eval_end_year]['Renting Total Assets'].iloc[0] if eval_end_year in temp_df['Year'].values else 0
        scenario_data.append({
            'Appreciation Rate (%)': appr,
            'VTI Return (%)': vti,
            'Wealth Difference': final_wealth_diff
        })

scenario_df = pd.DataFrame(scenario_data)

# Heatmap
heatmap = alt.Chart(scenario_df).mark_rect().encode(
    x=alt.X('Appreciation Rate (%):O', title='Housing Appreciation Rate (%)'),
    y=alt.Y('VTI Return (%):O', title='VTI Annual Return (%)'),
    color=alt.Color('Wealth Difference:Q', scale=alt.Scale(scheme='bluegreen', domainMid=0), title='Wealth Difference ($)'),
    tooltip=[
        alt.Tooltip('Appreciation Rate (%):Q', format='.1f'),
        alt.Tooltip('VTI Return (%):Q', format='.1f'),
        alt.Tooltip('Wealth Difference:Q', format='$,.2f')
    ]
).properties(
    title=f"Wealth Difference in {eval_end_year} by Scenario",
    width=400,
    height=400
)

st.altair_chart(heatmap, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Developed by Eric Hubbard | [KnowTheCostFinancial.com](https://knowthecostfinancial.com)")