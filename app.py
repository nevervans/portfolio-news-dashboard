import streamlit as st
import pandas as pd
import feedparser
from urllib.parse import quote
from datetime import datetime
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

st.set_page_config(page_title="PortfolioPulse", layout="wide")

st.title("📊 PortfolioPulse")
st.caption("AI-powered portfolio intelligence dashboard for retail investors")

# -------------------------
# Helper Functions
# -------------------------

def clean_ticker(ticker):
    return ticker.strip().upper()


@st.cache_data(ttl=600)
def fetch_news(stock):

    query = f"{stock} stock OR {stock} NSE OR {stock} BSE India"
    encoded_query = quote(query)

    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    feed = feedparser.parse(rss_url)

    articles = []

    for entry in feed.entries[:10]:

        articles.append({
            "Stock": stock,
            "Title": entry.title,
            "Source": entry.source.title if "source" in entry else "Google News",
            "Published": entry.published if "published" in entry else "",
            "Link": entry.link
        })

    return articles


def get_sentiment(text):

    score = analyzer.polarity_scores(text)["compound"]

    if score > 0.2:
        return "🟢 Positive"
    elif score < -0.2:
        return "🔴 Negative"
    else:
        return "🟡 Neutral"


def tag_news(title):

    t = title.lower()

    if "earnings" in t or "results" in t:
        return "📊 Earnings"

    if "acquire" in t or "merger" in t:
        return "🤝 M&A"

    if "upgrade" in t:
        return "⬆️ Upgrade"

    if "downgrade" in t:
        return "⬇️ Downgrade"

    if "rbi" in t or "regulatory" in t:
        return "⚖️ Regulation"

    return ""


def summarize_news(title):

    words = title.split()

    if len(words) <= 20:
        return title

    return " ".join(words[:20]) + "..."


def detect_risk(title):

    risk_words = [
        "downgrade",
        "fraud",
        "probe",
        "penalty",
        "lawsuit",
        "decline",
        "loss",
        "regulatory"
    ]

    t = title.lower()

    for word in risk_words:
        if word in t:
            return True

    return False


def parse_date(date_str):

    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")

    except:
        return None


def get_price(stock):

    try:

        ticker = yf.Ticker(f"{stock}.NS")

        data = ticker.history(period="1d")

        if data.empty:
            return None, None

        price = round(data["Close"].iloc[-1],2)

        change = round(((data["Close"].iloc[-1] - data["Open"].iloc[-1]) / data["Open"].iloc[-1])*100,2)

        return price, change

    except:

        return None, None


def get_price_history(stock, period):

    try:

        ticker = yf.Ticker(f"{stock}.NS")

        history = ticker.history(period=period)

        return history

    except:

        return None


# -------------------------
# Sidebar
# -------------------------

st.sidebar.header("Portfolio Input")

upload = st.sidebar.file_uploader(
    "Upload Portfolio (CSV or Excel)",
    type=["csv","xlsx"]
)

manual = st.sidebar.text_input(
    "Or enter tickers manually",
    placeholder="RELIANCE, TCS, INFY"
)

period_choice = st.sidebar.selectbox(
    "Select price chart period",
    ["1mo","6mo","1y","5y"],
    index=2
)

build = st.sidebar.button("Build Dashboard")

tickers = []

# -------------------------
# Extract Tickers
# -------------------------

if upload:

    if upload.name.endswith(".csv"):
        df_port = pd.read_csv(upload)
    else:
        df_port = pd.read_excel(upload)

    tickers = df_port.iloc[:,0].astype(str).apply(clean_ticker).tolist()

elif manual:

    tickers = [clean_ticker(t) for t in manual.split(",") if t.strip()]


# -------------------------
# Build Dashboard
# -------------------------

if build and tickers:

    all_news = []

    with st.spinner("Fetching portfolio news..."):

        with ThreadPoolExecutor() as executor:

            results = executor.map(fetch_news, tickers)

        for r in results:
            all_news.extend(r)

    if not all_news:

        st.warning("No news found.")

    else:

        df = pd.DataFrame(all_news)

        df["ParsedDate"] = df["Published"].apply(parse_date)

        df["Sentiment"] = df["Title"].apply(get_sentiment)

        df["Tag"] = df["Title"].apply(tag_news)

        df["Summary"] = df["Title"].apply(summarize_news)

        df["Risk"] = df["Title"].apply(detect_risk)

        df = df.sort_values(by="ParsedDate", ascending=False)

        # -------------------------
        # Risk Alerts
        # -------------------------

        st.subheader("⚠️ Portfolio Alerts")

        alerts = df[df["Risk"] == True]

        if alerts.empty:

            st.write("No major risk alerts detected.")

        else:

            for _, row in alerts.head(5).iterrows():

                st.warning(f"{row['Stock']}: {row['Title']}")

        st.divider()

        # -------------------------
        # Stock Sections
        # -------------------------

        for stock in tickers:

            price, change = get_price(stock)

            if price:

                arrow = "▲" if change >= 0 else "▼"

                st.header(f"{stock} — ₹{price} {arrow}{change}%")

            else:

                st.header(stock)

            # Fundamentals links

            screener_url = f"https://www.screener.in/company/{stock}/"
            tickertape_url = f"https://www.tickertape.in/stocks/{stock.lower()}"

            col1, col2 = st.columns(2)

            col1.markdown(f"[📊 View Fundamentals on Screener]({screener_url})")
            col2.markdown(f"[📈 View Full Analysis on Tickertape]({tickertape_url})")

            # Price chart

            history = get_price_history(stock, period_choice)

            if history is not None and not history.empty:

                st.subheader("📈 Price Chart")

                st.line_chart(history["Close"])

            st.subheader("Latest News")

            stock_df = df[df["Stock"] == stock]

            if stock_df.empty:

                st.write("No recent news.")

            else:

                for _, row in stock_df.iterrows():

                    with st.container():

                        st.markdown(f"### {row['Title']}")

                        st.caption(
                            f"{row['Source']} | {row['Published']} | {row['Sentiment']} {row['Tag']}"
                        )

                        st.write(f"**Summary:** {row['Summary']}")

                        st.markdown(f"[Read Article]({row['Link']})")

                        st.divider()

else:

    st.info("Upload a portfolio or enter tickers to build your dashboard.")
