import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

ROOMMATES = ["SAFI", "GANDOFLY", "LOLO", "JOJO", "BODY", "PAKI"]
CURRENCY = "EGP" 

@st.cache_resource
def connect_to_sheet():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
        sheet_id = st.secrets["sheets"]["id"]
        sheet = client.open_by_key(sheet_id)
        return sheet
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheets: {e}")
        return None

def read_expenses(sheet):
    try:
        worksheet = sheet.worksheet("Expenses")
        data = worksheet.get_all_records()
        return data
    except:
        return []

def read_payments(sheet):
    try:
        worksheet = sheet.worksheet("Payments")
        data = worksheet.get_all_records()
        return data
    except:
        return []

def add_expense(sheet, date, description, payer, amount, shared_with, notes):
    try:
        worksheet = sheet.worksheet("Expenses")
        shared_str = ", ".join(shared_with)
        worksheet.append_row([date, description, payer, float(amount), shared_str, notes])
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def add_payment(sheet, date, from_person, to_person, amount, notes):
    try:
        worksheet = sheet.worksheet("Payments")
        worksheet.append_row([date, from_person, to_person, float(amount), notes])
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def apply_custom_css():
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        header {visibility: hidden !important;}
        .stDeployButton {display: none !important;}
        .viewerBadge_container__1QSob {display: none !important;}
        .styles_viewerBadge__1yB5_ {display: none !important;}
        div[data-testid="stToolbar"] {display: none !important;}
        div[data-testid="stDecoration"] {display: none !important;}
        div[data-testid="stStatusWidget"] {display: none !important;}
        #MainMenu {display: none !important;}
        footer {display: none !important;}
        header {display: none !important;}
        
        .stApp {
            background-color: #f5f7fa;
        }
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }
        .balance-positive { color: #28a745; font-weight: bold; }
        .balance-negative { color: #dc3545; font-weight: bold; }
        .balance-zero { color: #6c757d; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

def calculate_balances(expenses, payments):
    balances = {person: 0.0 for person in ROOMMATES}
    
    for expense in expenses:
        payer = expense["Payer"]
        amount = float(expense["Amount"])
        shared_str = expense["Shared With"]
        shared_with = [s.strip() for s in shared_str.split(",")] if shared_str else []
        
        if len(shared_with) > 0:
            split_amount = amount / len(shared_with)
            balances[payer] += amount
            
            for person in shared_with:
                if person in balances:
                    balances[person] -= split_amount
    
    for payment in payments:
        from_person = payment["From"]
        to_person = payment["To"]
        amount = float(payment["Amount"])
        
        if from_person in balances:
            balances[from_person] += amount
        if to_person in balances:
            balances[to_person] -= amount
    
    return balances

def calculate_settlement(balances):
    creditors = []
    debtors = []
    
    for person, balance in balances.items():
        if balance > 0.01:
            creditors.append({"name": person, "amount": balance})
        elif balance < -0.01:
            debtors.append({"name": person, "amount": -balance})
    
    creditors.sort(key=lambda x: x["amount"], reverse=True)
    debtors.sort(key=lambda x: x["amount"], reverse=True)
    
    settlements = []
    i, j = 0, 0
    
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        transfer = min(debtor["amount"], creditor["amount"])
        
        if transfer > 0.01:
            settlements.append({
                "from": debtor["name"],
                "to": creditor["name"],
                "amount": round(transfer, 2)
            })
        
        debtor["amount"] -= transfer
        creditor["amount"] -= transfer
        
        if debtor["amount"] < 0.01:
            i += 1
        if creditor["amount"] < 0.01:
            j += 1
    
    return settlements

def main():
    st.set_page_config(
        page_title="Roommate Expense Tracker",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    apply_custom_css()
    
    st.markdown("""
    <div class="main-header">
        <h1>🏠 Roommate Expense Tracker</h1>
        <p>Split expenses fairly with Google Sheets sync</p>
    </div>
    """, unsafe_allow_html=True)
    
    sheet = connect_to_sheet()
    
    if not sheet:
        st.error("❌ Cannot connect to Google Sheets. Check your configuration.")
        st.stop()
    
    expenses = read_expenses(sheet)
    payments = read_payments(sheet)
    balances = calculate_balances(expenses, payments)
    settlements = calculate_settlement(balances)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Add Expense", "💸 Add Payment", "📜 History"])
    
    with tab1:
        col1, col2, col3 = st.columns(3)
        
        total_expenses = sum(float(e["Amount"]) for e in expenses)
        total_payments = sum(float(p["Amount"]) for p in payments)
        
        with col1:
            st.metric("Total Expenses", f"{CURRENCY} {total_expenses:.2f}")
        with col2:
            st.metric("Total Payments", f"{CURRENCY} {total_payments:.2f}")
        with col3:
            st.metric("Transactions", len(expenses) + len(payments))
        
        st.markdown("---")
        st.subheader("💰 Current Balances")
        
        cols = st.columns(len(ROOMMATES))
        for i, person in enumerate(ROOMMATES):
            balance = balances[person]
            with cols[i]:
                st.markdown(f"**{person}**")
                if balance > 0.01:
                    st.markdown(f'<p class="balance-positive">+{balance:.2f} {CURRENCY}</p>', unsafe_allow_html=True)
                    st.caption("Is owed")
                elif balance < -0.01:
                    st.markdown(f'<p class="balance-negative">{balance:.2f} {CURRENCY}</p>', unsafe_allow_html=True)
                    st.caption("Owes")
                else:
                    st.markdown(f'<p class="balance-zero">0.00 {CURRENCY}</p>', unsafe_allow_html=True)
                    st.caption("Settled")
        
        st.markdown("---")
        st.subheader("🔄 Settlement Plan")
        
        if not settlements:
            st.success("🎉 Everyone is settled up!")
        else:
            for settlement in settlements:
                st.info(f"**{settlement['from']}** pays **{settlement['to']}**: {settlement['amount']:.2f} {CURRENCY}")
    
    with tab2:
        st.subheader("➕ Add New Expense")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_date = st.date_input("Date", datetime.now())
                expense_description = st.text_input("Description", placeholder="e.g., Groceries, Utilities")
                expense_payer = st.selectbox("Who paid?", ROOMMATES)
            
            with col2:
                expense_amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=0.01)
                st.markdown("**Who shares this expense?**")
                shared_with = []
                for person in ROOMMATES:
                    if st.checkbox(person, value=True, key=f"share_{person}"):
                        shared_with.append(person)
            
            expense_notes = st.text_area("Notes (optional)")
            submit = st.form_submit_button("💾 Add Expense")
            
            if submit:
                if not expense_description:
                    st.error("Please enter a description")
                elif expense_amount <= 0:
                    st.error("Amount must be positive")
                elif len(shared_with) == 0:
                    st.error("Select at least one person")
                else:
                    date_str = expense_date.strftime("%Y-%m-%d")
                    if add_expense(sheet, date_str, expense_description, expense_payer, 
                                   expense_amount, shared_with, expense_notes):
                        split = expense_amount / len(shared_with)
                        st.success(f"✅ Added! {expense_payer} paid {expense_amount:.2f} {CURRENCY}, split {split:.2f} each")
                        st.balloons()
                        st.rerun()
    
    with tab3:
        st.subheader("💸 Record Payment")
        
        with st.form("payment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                payment_date = st.date_input("Date", datetime.now())
                payment_from = st.selectbox("From", ROOMMATES)
            
            with col2:
                payment_to = st.selectbox("To", ROOMMATES)
                payment_amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=0.01)
            
            payment_notes = st.text_area("Notes (optional)")
            submit = st.form_submit_button("💾 Record Payment")
            
            if submit:
                if payment_from == payment_to:
                    st.error("Payer and recipient must be different")
                elif payment_amount <= 0:
                    st.error("Amount must be positive")
                else:
                    date_str = payment_date.strftime("%Y-%m-%d")
                    if add_payment(sheet, date_str, payment_from, payment_to, 
                                   payment_amount, payment_notes):
                        st.success(f"✅ Payment recorded! {payment_from} paid {payment_amount:.2f} {CURRENCY} to {payment_to}")
                        st.rerun()
    
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 Expense History")
            if expenses:
                for exp in reversed(expenses):
                    with st.expander(f"{exp['Date']} - {exp['Description']} ({exp['Amount']} {CURRENCY})"):
                        st.write(f"**Paid by:** {exp['Payer']}")
                        st.write(f"**Shared by:** {exp['Shared With']}")
                        if exp.get('Notes'):
                            st.write(f"**Notes:** {exp['Notes']}")
            else:
                st.info("No expenses yet")
        
        with col2:
            st.subheader("💸 Payment History")
            if payments:
                for pay in reversed(payments):
                    with st.expander(f"{pay['Date']} - {pay['Amount']} {CURRENCY}"):
                        st.write(f"**From:** {pay['From']}")
                        st.write(f"**To:** {pay['To']}")
                        if pay.get('Notes'):
                            st.write(f"**Notes:** {pay['Notes']}")
            else:
                st.info("No payments yet")

if __name__ == "__main__":
    main()
