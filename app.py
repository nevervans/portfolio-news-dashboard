import streamlit as st
import feedparser
from datetime import datetime
import pandas as pd

def clean_ticker(ticker):
    return ticker.strip().upper()

def fetch_news_for_stock(stock):
    query = f"{stock} NSE OR {stock} BSE"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
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

def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
    except:
        return None

st.set_page_config(page_title="Portfolio News Dashboard", layout="wide")

st.title("📊 Portfolio-Aware Finance News Dashboard")
st.caption("Personalised news for your Indian equity portfolio")

st.sidebar.header("Your Portfolio")
tickers_input = st.sidebar.text_area(
    "Enter stock tickers (comma-separated)",
    placeholder="RELIANCE, TCS, HDFCBANK, INFY"
)

build = st.sidebar.button("Build My Dashboard")

if build and tickers_input:
    tickers = [clean_ticker(t) for t in tickers_input.split(",") if t.strip()]
    all_news = []

    with st.spinner("Fetching relevant news..."):
        for stock in tickers:
            all_news.extend(fetch_news_for_stock(stock))

    if not all_news:
        st.warning("No news found. Try different tickers.")
    else:
        df = pd.DataFrame(all_news)
        df["ParsedDate"] = df["Published"].apply(format_date)
        df = df.sort_values(by="ParsedDate", ascending=False)

        for stock in tickers:
            st.subheader(f"🧾 {stock}")
            stock_df = df[df["Stock"] == stock]

            if stock_df.empty:
                st.write("No recent news found.")
            else:
                for _, row in stock_df.iterrows():
                    st.markdown(f"**{row['Title']}**")
                    st.caption(f"{row['Source']} | {row['Published']}")
                    st.markdown(f"[Read more]({row['Link']})")
                    st.markdown("---")
else:
    st.info("Enter your portfolio tickers in the sidebar and click Build My Dashboard.")
