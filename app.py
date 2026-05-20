from google import genai
from google.genai.errors import APIError
import streamlit as st
import pandas as pd
import altair as alt

# =====================================================================
# 1. API CONFIGURATION
# =====================================================================
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    st.error("🔑 Configuration Secret Missing: Please verify your hidden `.streamlit/secrets.toml` file.")
    st.stop()

# =====================================================================
# 2. PAGE CONFIGURATION & STYLING
# =====================================================================
st.set_page_config(page_title="Executive Sales Dashboard", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1 { color: #0F172A; font-weight: 700; font-size: 2.2rem !important; }
        h2 { color: #1E293B; font-weight: 600; font-size: 1.5rem !important; margin-top: 1rem; border-bottom: 2px solid #F1F5F9; padding-bottom: 0.4rem; }
        h3 { color: #334155; font-weight: 600; font-size: 1.1rem !important; }
        .stButton>button { background-color: #1E3A8A; color: white; border-radius: 4px; border: none; font-weight: 500; padding: 0.5rem 2rem; }
        .stButton>button:hover { background-color: #2563EB; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Executive Sales & Profitability Dashboard")

# =====================================================================
# 3. DATA LOADING & PROCESSING
# =====================================================================
uploaded_file = st.file_uploader("Upload 'ai_business_sales_dataset.csv'", type=["csv"])

if uploaded_file:
    # Load data
    df = pd.read_csv(uploaded_file)
    
    # Clean and parse the dates specifically for this dataset
    df['Order_Date'] = pd.to_datetime(df['Order_Date'])
    df['Month_Year'] = df['Order_Date'].dt.to_period('M').astype(str)
    
    # Reset AI memory if a fresh file is uploaded
    if "active_file" not in st.session_state or st.session_state["active_file"] != uploaded_file.name:
        st.session_state["active_file"] = uploaded_file.name
        if "saved_brief" in st.session_state:
            del st.session_state["saved_brief"]

    # =====================================================================
    # 4. SIDEBAR FILTERS (Only possible because we hardcoded the schema!)
    # =====================================================================
    st.sidebar.header("🎯 Dashboard Filters")
    selected_regions = st.sidebar.multiselect("Select Regions:", options=df['Region'].unique(), default=df['Region'].unique())
    selected_segments = st.sidebar.multiselect("Select Segments:", options=df['Segment'].unique(), default=df['Segment'].unique())
    
    # Apply Filters
    filtered_df = df[(df['Region'].isin(selected_regions)) & (df['Segment'].isin(selected_segments))]

    if filtered_df.empty:
        st.warning("⚠️ No data available for the selected filters.")
        st.stop()

    # =====================================================================
    # 5. CORE KPI METRICS
    # =====================================================================
    st.subheader("📊 Global Performance Metrics")
    
    total_sales = filtered_df['Sales'].sum()
    total_profit = filtered_df['Profit'].sum()
    profit_margin = (total_profit / total_sales) * 100 if total_sales > 0 else 0
    total_orders = filtered_df['Order_ID'].nunique()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Gross Sales", f"${total_sales:,.0f}")
    with col2:
        st.metric("Total Net Profit", f"${total_profit:,.0f}")
    with col3:
        st.metric("Blended Profit Margin", f"{profit_margin:.1f}%")
    with col4:
        st.metric("Total Unique Orders", f"{total_orders:,}")

    # =====================================================================
    # 6. TAILORED VISUALIZATIONS
    # =====================================================================
    st.subheader("📈 Revenue & Profitability Trends")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("**Monthly Sales Trend**")
        monthly_sales = filtered_df.groupby('Month_Year', as_index=False)['Sales'].sum()
        
        line_chart = alt.Chart(monthly_sales).mark_line(color="#2563EB", strokeWidth=3, point=True).encode(
            x=alt.X('Month_Year:N', title='Month', sort=None),
            y=alt.Y('Sales:Q', title='Total Sales ($)'),
            tooltip=['Month_Year', alt.Tooltip('Sales:Q', format=',.2f')]
        ).properties(height=350)
        st.altair_chart(line_chart, use_container_width=True)

    with chart_col2:
        st.markdown("**Profit by Sub-Category**")
        subcat_profit = filtered_df.groupby('Sub_Category', as_index=False)['Profit'].sum()
        
        # Color red if negative profit, blue if positive
        bar_chart = alt.Chart(subcat_profit).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
            x=alt.X('Sub_Category:N', sort='-y', title='Sub-Category'),
            y=alt.Y('Profit:Q', title='Total Profit ($)'),
            color=alt.condition(
                alt.datum.Profit > 0,
                alt.value("#1E3A8A"),  # Blue for positive
                alt.value("#DC2626")   # Red for negative
            ),
            tooltip=['Sub_Category', alt.Tooltip('Profit:Q', format=',.2f')]
        ).properties(height=350)
        st.altair_chart(bar_chart, use_container_width=True)

    # =====================================================================
    # 7. HYPER-SPECIFIC AI BRIEFING GENERATOR
    # =====================================================================
    st.subheader("🧠 Strategic AI Analysis")
    st.write("Generate a bespoke executive summary based on the currently filtered data parameters.")
    
    if st.button("Generate Executive Briefing"):
        with st.spinner("AI is synthesizing regional and categorical performance..."):
            
            # Pre-calculate explicit business insights for the AI to base its report on
            top_region = filtered_df.groupby('Region')['Sales'].sum().idxmax()
            top_category = filtered_df.groupby('Category')['Profit'].sum().idxmax()
            
            # Create a heavily structured, dataset-specific prompt
            prompt = f"""
            You are a Chief Revenue Officer. Write a sharp, formal executive briefing based on this precise data snapshot:
            
            CURRENT SNAPSHOT DATA:
            - Total Sales: ${total_sales:,.2f}
            - Total Profit: ${total_profit:,.2f}
            - Profit Margin: {profit_margin:.1f}%
            - Top Performing Region by Sales: {top_region}
            - Most Profitable Category: {top_category}
            
            Format your response cleanly with exactly 3 professional sections:
            
            ### 📈 Financial Health Assessment
            [Assess the overall sales and profit margin performance. Is the margin healthy?]
            
            ### 🎯 Categorical & Regional Strengths
            [Highlight the success in the top region and category provided.]
            
            ### 💡 Strategic Next Steps
            [Provide 2 actionable recommendations based strictly on managing physical product sales, shipping costs, or regional expansion.]
            """
            
            try:
                # Attempt to call the live Google AI API
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                st.session_state["saved_brief"] = response.text
                st.success("Executive briefing compiled successfully via live AI.")
                
            except APIError as e:
                # Catch 503 Server Errors and deploy the dynamic portfolio fallback
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    st.warning("⚠️ Live AI Servers are currently at maximum global capacity. Deploying simulated executive briefing for demonstration purposes.")
                    
                    # This mock report uses your REAL data variables so it still looks incredibly smart!
                    mock_brief = f"""
### 📈 Financial Health Assessment
The current sales volume of **${total_sales:,.2f}** demonstrates strong market traction. With a net profit of **${total_profit:,.2f}**, the blended profit margin sits at **{profit_margin:.1f}%**, indicating a stable financial baseline but leaving room for supply chain optimization.

### 🎯 Categorical & Regional Strengths
The **{top_region}** region continues to dramatically outperform expectations, acting as the primary driver for top-line revenue. Furthermore, the **{top_category}** segment remains our most profitable asset, heavily anchoring the company's net positive cash flow.

### 💡 Strategic Next Steps
1. **Accelerate Regional Logistics:** Allocate marketing and warehousing budgets heavily toward the **{top_region}** to capitalize on current buyer momentum and reduce regional shipping overhead.
2. **Category Emulation:** Conduct an immediate audit of the **{top_category}** pricing and vendor strategy, and apply those exact margins to our lowest-performing sub-categories.
                    """
                    st.session_state["saved_brief"] = mock_brief
                    
                # Catch 429 Rate Limit Errors
                elif "429" in str(e) or "ResourceExhausted" in str(e):
                    st.error("⚠️ **Free Tier Speed Limit Active:** You are clicking too fast. Please wait 15 seconds and try again.")
                else:
                    st.error(f"API Error encountered: {e}")
            except Exception as e:
                st.error(f"System Exception encountered: {e}")

    # Keep the brief pinned to the bottom of the screen
    if "saved_brief" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["saved_brief"])