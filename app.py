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
    This dashboard helps you decide whether to **rent or buy** your primary residence by analyzing mortgage costs and comparing total expenses.

    **Key Outputs:**
    - Unified amortization schedule (monthly by default, biweekly if selected, with refinance transition if enabled).
    - Metrics for the main scenario (with refinance if enabled).
    - Savings from refinance (interest saved, payoff difference).
    - Savings from biweekly payments (interest saved, payoff difference, shown if biweekly selected).
    - Cost comparison: Total buying expenses vs. renting expenses over the evaluation period.

    **How to Use:**
    1. Enter purchase details, loan terms, and mortgage type.
    2. Specify extra payments, buy points, and refinance options (if applicable).
    3. Review metrics, schedule, and cost comparison.
    4. Download the schedule for further analysis.

    **Methodology:**
    - Monthly payments: 12 payments/year (default).
    - Biweekly payments: 26 payments/year (equivalent to 13 monthly payments, shown as a comparison if selected).
    - Variable-rate mortgages adjust based on your rate schedule.
    - Extra payments reduce principal and interest, applied consistently.
    - Buy points reduce the mortgage rate (1 point = 1% of loan amount).
    - Refinance integrates into the schedule, showing the transition (highlighted in blue) and savings.
    - PMI applies until equity reaches the threshold.
    - Buying costs: Mortgage (P&I + PMI + extra), taxes (increase with appreciation), insurance (increase with insurance rate), maintenance (increase with maintenance rate), emergency (one-time), points/upfront refinance costs.
    - Renting costs: Monthly rent * 12, increasing annually.
    """)

# ----------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.image("https://via.placeholder.com/250", caption="EyesWideOpenLogo")  # Replace with actual logo URL
    st.markdown("Tool developed by Eric Hubbard")
    st.markdown("[KnowTheCostFinancial.com](https://knowthecostfinancial.com)")

    # 1️⃣ General Inputs
    with st.expander("General Inputs", expanded=True):
        eval_start_year = st.number_input("Evaluation Start Year", value=2025, step=1, min_value=2000, max_value=2100)
        eval_end_year = st.number_input("Evaluation End Year", value=2070, step=1, min_value=eval_start_year, max_value=2100)

    # 2️⃣ Purchase Details
    with st.expander("Purchase Details", expanded=True):
        purchase_year = st.number_input("Purchase Year", value=2025, step=1, min_value=eval_start_year, max_value=eval_end_year)
        purchase_price = st.number_input("Purchase Price ($)", value=500_000, step=10_000, min_value=0)
        down_payment = st.number_input("Down Payment ($)", value=100_000, step=1_000, min_value=0, max_value=purchase_price)
        loan_amount = purchase_price - down_payment
        percent_down = (down_payment / purchase_price * 100) if purchase_price > 0 else 0
        st.metric("Loan Amount", f"${loan_amount:,.0f}")
        st.metric("% Down Payment", f"{percent_down:.2f}%")

    # 3️⃣ Loan Terms & Mortgage
    with st.expander("Loan Terms & Mortgage", expanded=True):
        loan_years = st.number_input("Loan Length (Years)", value=30, step=1, min_value=1, max_value=50)
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.01, min_value=0.0, format="%.3f")
        pmi_rate = st.number_input("PMI Rate (%)", value=0.20, step=0.01, min_value=0.0)
        pmi_equity_threshold = st.number_input("PMI Paid Until Equity (%)", value=20, step=1, min_value=0, max_value=100)
        payment_frequency = st.radio("Payment Frequency", ["Monthly", "Biweekly"], index=0)
        mortgage_type = st.radio("Mortgage Type", ["Fixed", "Variable"], index=0)

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

    # Buy Points Option
    with st.expander("Buy Points Option", expanded=False):
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
            points_cost = points * (loan_amount * 0.01)  # 1 point = 1% of loan
            st.metric("Effective Rate After Points", f"{effective_rate:.3f}%")
            st.metric("Points Cost", f"${points_cost:,.2f}")

    # 4️⃣ Refinance Options
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

        if show_refinance:
            refi_rate = st.number_input("Refinance Rate (%)", value=5.0, step=0.01, min_value=0.0, format="%.3f")
            refi_term_years = st.number_input("Refinance Term (Years)", value=30, step=1, min_value=1, max_value=50)
            refi_start_date = st.date_input("Refinance Start Date", min_value=datetime(purchase_year, 1, 1), max_value=datetime(purchase_year + loan_years, 12, 31))
            refi_costs = st.number_input("Closing Costs ($)", value=3000, step=500, min_value=0)
            roll_costs = st.radio("Refinance Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0)
            refi_payment_frequency = st.radio("Refinance Payment Frequency", ["Monthly", "Biweekly"], index=0)
            refi_mortgage_type = st.radio("Refinance Mortgage Type", ["Fixed", "Variable"], index=0)
            refi_periods_per_year = 12 if refi_payment_frequency == "Monthly" else 26

            if refi_mortgage_type == "Variable":
                st.subheader("Refinance Variable Rate Schedule")
                default_refi_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [refi_rate, 6.5, 7.0]})
                refi_rate_schedule = st.data_editor(
                    default_refi_schedule,
                    column_config={
                        "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=refi_term_years, step=1),
                        "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1)
                    },
                    hide_index=True,
                    num_rows="dynamic"
                )

    # 5️⃣ Extra Principal Payments
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

    # 6️⃣ Ongoing Expenses
    with st.expander("Ongoing Expenses", expanded=False):
        default_property_expenses = pd.DataFrame({
            "Category": ["Property Taxes", "Home Insurance", "Routine Maintenance"],
            "Amount ($)": [8000, 1100, 6000]
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

    # 7️⃣ Appreciation & Growth
    with st.expander("Appreciation & Growth", expanded=False):
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=3.5, step=0.1, min_value=0.0)
        annual_maintenance_increase = st.number_input("Annual Maintenance Increase (%)", value=3.0, step=0.1, min_value=0.0)
        annual_insurance_increase = st.number_input("Annual Insurance Increase (%)", value=3.0, step=0.1, min_value=0.0)

    # 8️⃣ Rental Assumptions
    with st.expander("Rental Assumptions", expanded=False):
        cost_of_rent = st.number_input("Initial Monthly Rent ($)", value=3000, step=50, min_value=0)
        annual_rent_increase = st.number_input("Annual Rent Increase (%)", value=4.0, step=0.1, min_value=0.0)

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

def get_remaining_balance(schedule_df, refi_date):
    refi_date = pd.to_datetime(refi_date)
    mask = schedule_df["Date"] <= refi_date
    return schedule_df.loc[mask, "Balance"].iloc[-1] if mask.any() else schedule_df["Balance"].iloc[0]

def calculate_cost_comparison(annual_df, edited_property_expenses, edited_emergency_expenses, purchase_year, eval_start_year, eval_end_year, annual_appreciation, annual_insurance_increase, annual_maintenance_increase, cost_of_rent, annual_rent_increase, points_cost, points_cost_method, refi_costs, roll_costs):
    years = range(max(purchase_year, eval_start_year), min(purchase_year + loan_years, eval_end_year) + 1)
    comparison_data = []
    cumulative_buy = 0
    cumulative_rent = 0
    taxes = edited_property_expenses[edited_property_expenses["Category"] == "Property Taxes"]["Amount ($)"].iloc[0] if "Property Taxes" in edited_property_expenses["Category"].values else 0
    insurance = edited_property_expenses[edited_property_expenses["Category"] == "Home Insurance"]["Amount ($)"].iloc[0] if "Home Insurance" in edited_property_expenses["Category"].values else 0
    maintenance = edited_property_expenses[edited_property_expenses["Category"] == "Routine Maintenance"]["Amount ($)"].iloc[0] if "Routine Maintenance" in edited_property_expenses["Category"].values else 0
    current_rent = cost_of_rent
    upfront_costs = points_cost if points_cost_method == "Pay Upfront" else 0
    for year in years:
        year_idx = year - purchase_year
        mortgage_cost = annual_df[annual_df["Date"].dt.year == year]["Payment"].sum() + annual_df[annual_df["Date"].dt.year == year]["PMI"].sum() + annual_df[annual_df["Date"].dt.year == year]["Extra"].sum() if year in annual_df["Date"].dt.year.values else 0
        year_taxes = taxes * (1 + annual_appreciation / 100) ** year_idx
        year_insurance = insurance * (1 + annual_insurance_increase / 100) ** year_idx
        year_maintenance = maintenance * (1 + annual_maintenance_increase / 100) ** year_idx
        year_emergency = edited_emergency_expenses[edited_emergency_expenses["Year"] == year]["Amount ($)"].sum() if not edited_emergency_expenses.empty else 0
        year_upfront = upfront_costs if year == purchase_year else (refi_costs if show_refinance and roll_costs == "Pay Upfront" and refi_start_date and refi_start_date.year == year else 0)
        buy_cost = mortgage_cost + year_taxes + year_insurance + year_maintenance + year_emergency + year_upfront
        rent_cost = current_rent * 12
        cumulative_buy += buy_cost
        cumulative_rent += rent_cost
        comparison_data.append({
            "Year": year,
            "Buying Cost": buy_cost,
            "Renting Cost": rent_cost,
            "Cumulative Buying Cost": cumulative_buy,
            "Cumulative Renting Cost": cumulative_rent
        })
        current_rent *= (1 + annual_rent_increase / 100)

    return pd.DataFrame(comparison_data)

# ----------------------------- CALCULATIONS -----------------------------
# Adjust principal and rate based on points
effective_principal = loan_amount + (points_cost if points_cost_method == "Add to Loan Balance" else 0)
effective_mortgage_rate = effective_rate

# Extra payments schedule based on selected frequency
extra_schedule = expand_extra_payments(extra_payments, purchase_year, loan_years, payment_frequency)

# No-refi schedule (always monthly, for refinance comparison)
no_refi_schedule_df, no_refi_monthly_df, no_refi_annual_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=12,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=expand_extra_payments(extra_payments, purchase_year, loan_years, "Monthly"),
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price
)

# Monthly comparison schedule (for biweekly savings)
monthly_comparison_df, _, _ = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=12,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=expand_extra_payments(extra_payments, purchase_year, loan_years, "Monthly"),
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price,
    refi_start_date=refi_start_date if show_refinance else None,
    refi_principal=(get_remaining_balance(no_refi_schedule_df, refi_start_date) + (refi_costs if roll_costs == "Add to Loan Balance" else 0)) if show_refinance and refi_start_date else None,
    refi_years=refi_term_years,
    refi_periods_per_year=refi_periods_per_year if show_refinance else None,
    refi_rate_schedule=refi_rate_schedule,
    refi_mortgage_type=refi_mortgage_type,
    refi_mortgage_rate=refi_rate
)

# Biweekly comparison schedule (for monthly main schedule)
biweekly_schedule_df, _, _ = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=26,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=expand_extra_payments(extra_payments, purchase_year, loan_years, "Biweekly"),
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price,
    refi_start_date=refi_start_date if show_refinance else None,
    refi_principal=(get_remaining_balance(no_refi_schedule_df, refi_start_date) + (refi_costs if roll_costs == "Add to Loan Balance" else 0)) if show_refinance and refi_start_date else None,
    refi_years=refi_term_years,
    refi_periods_per_year=refi_periods_per_year if show_refinance else None,
    refi_rate_schedule=refi_rate_schedule,
    refi_mortgage_type=refi_mortgage_type,
    refi_mortgage_rate=refi_rate
)

# Main schedule (monthly by default, biweekly if selected)
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
    refi_principal=(get_remaining_balance(no_refi_schedule_df, refi_start_date) + (refi_costs if roll_costs == "Add to Loan Balance" else 0)) if show_refinance and refi_start_date else None,
    refi_years=refi_term_years,
    refi_periods_per_year=refi_periods_per_year if show_refinance else None,
    refi_rate_schedule=refi_rate_schedule,
    refi_mortgage_type=refi_mortgage_type,
    refi_mortgage_rate=refi_rate
)

# Main Metrics (main schedule)
monthly_payment = main_schedule_df['Payment'].iloc[0] if main_periods_per_year == 12 else main_schedule_df['Payment'].iloc[0] * 26 / 12
payment_per_period = main_schedule_df['Payment'].iloc[0]
total_interest = main_schedule_df['Interest'].sum()
total_pmi = main_schedule_df['PMI'].sum()
payoff_years = len(main_schedule_df) / main_periods_per_year

# Savings from refinance (if enabled)
interest_saved_refi = 0
pmi_saved_refi = 0
payoff_difference_refi = 0
if show_refinance and refi_start_date:
    interest_saved_refi = no_refi_schedule_df['Interest'].sum() - total_interest
    pmi_saved_refi = no_refi_schedule_df['PMI'].sum() - total_pmi
    payoff_difference_refi = len(no_refi_schedule_df) / 12 - payoff_years

# Savings from biweekly (if biweekly selected)
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
    cost_of_rent, 
    annual_rent_increase,
    points_cost,
    points_cost_method,
    refi_costs,
    roll_costs
)

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
    st.subheader("Refinance Savings")
    with st.container(border=True):
        cols = st.columns(3)
        if interest_saved_refi >= 0:
            cols[0].metric("Interest Saved", f"${interest_saved_refi:,.2f}")
        else:
            cols[0].metric("Additional Interest", f"${abs(interest_saved_refi):,.2f}")
        if pmi_saved_refi >= 0:
            cols[1].metric("PMI Saved", f"${pmi_saved_refi:,.2f}")
        else:
            cols[1].metric("Additional PMI", f"${abs(pmi_saved_refi):,.2f}")
        cols[2].metric("Payoff Time Difference", f"{abs(payoff_difference_refi):.1f} years {'shorter' if payoff_difference_refi >= 0 else 'longer'}")

if payment_frequency == "Biweekly":
    st.subheader("Biweekly Savings (Compared to Monthly)")
    with st.container(border=True):
        cols = st.columns(2)
        if interest_saved_biweekly >= 0:
            cols[0].metric("Interest Saved", f"${interest_saved_biweekly:,.2f}")
        else:
            cols[0].metric("Additional Interest", f"${abs(interest_saved_biweekly):,.2f}")
        cols[1].metric("Payoff Time Difference", f"{abs(payoff_difference_biweekly):.1f} years {'shorter' if payoff_difference_biweekly >= 0 else 'longer'}")

st.subheader("Amortization Schedule")
st.markdown("**Note**: 'Loan Type' column indicates 'Original' or 'Refinance' (highlighted in blue). 'Effective Rate (%)' shows the interest rate applied each period, reflecting points or variable rates.")
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

    # Truncate to the shorter schedule's end date
    max_date = chart_data.groupby('Schedule')['Date'].max().min()
    chart_data = chart_data[chart_data["Date"] <= max_date]

    line = alt.Chart(chart_data).mark_line().encode(
        x='Date:T',
        y=alt.Y('Balance:Q', title='Balance ($)'),
        color=alt.Color('Schedule:N', legend=alt.Legend(title="Schedule")),
        strokeDash=alt.condition(
            alt.datum.Schedule == "Original (No Refinance)",
            alt.value([5, 5]),
            alt.value([0])
        ),
        tooltip=['Date', 'Balance', 'Schedule']
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

    # Truncate to the shorter schedule's end date
    max_date = chart_data.groupby('Schedule')['Date'].max().min()
    chart_data = chart_data[chart_data["Date"] <= max_date]

    line = alt.Chart(chart_data).mark_line().encode(
        x='Date:T',
        y=alt.Y('Balance:Q', title='Balance ($)'),
        color=alt.Color('Schedule:N', legend=alt.Legend(title="Schedule")),
        strokeDash=alt.condition(
            alt.datum.Schedule == comparison_label,
            alt.value([5, 5]),
            alt.value([0])
        ),
        tooltip=['Date', 'Balance', 'Schedule']
    ).interactive()

    st.altair_chart(line, use_container_width=True)

st.subheader("Cost Comparison: Buy vs. Rent")
st.dataframe(
    cost_comparison_df.style.format({
        "Buying Cost": "${:,.2f}",
        "Renting Cost": "${:,.2f}",
        "Cumulative Buying Cost": "${:,.2f}",
        "Cumulative Renting Cost": "${:,.2f}"
    })
)

# ------------------------- DOWNLOAD -----------------------
st.subheader("Download Schedule")
st.download_button(
    label="Download Amortization Schedule",
    data=main_schedule_df.to_csv(index=False),
    file_name="amortization_schedule.csv",
    mime="text/csv"
)