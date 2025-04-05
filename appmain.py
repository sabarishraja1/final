import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import psycopg2
import pandas as pd
import re
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import nltk

# Download required resources
nltk.download('vader_lexicon')
nltk.download('stopwords')
from nltk.corpus import stopwords

# RDS Credentials
DB_HOST = "mydatas.cz86suuek39d.ap-south-1.rds.amazonaws.com"
DB_NAME = "final_data"
DB_USER = "pgadmin"
DB_PASSWORD = "Pgadmin123"

# Connect and fetch data from RDS
def fetch_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("✅ Connected to RDS")

        query = "SELECT * FROM NewsData"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print("❌ Error:", e)
        return None

# Clean text
def clean_text(text):
    if pd.isnull(text):
        return ""
    text = text.lower()
    text = re.sub(r'https?://\S+|[^a-zA-Z\s]', '', text)  # remove links, punctuation
    text = re.sub(r'\s+', ' ', text).strip()  # remove extra spaces
    stop_words = set(stopwords.words('english'))
    text = " ".join(word for word in text.split() if word not in stop_words)
    return text

# Sentiment Analysis
def add_sentiment(df):
    sia = SentimentIntensityAnalyzer()
    df["cleaned_headline"] = df["headline"].apply(clean_text)
    df["cleaned_description"] = df["short_description"].apply(clean_text)
    df["sentiment_score"] = df["cleaned_headline"].apply(lambda x: sia.polarity_scores(x)["compound"])
    df["neg"] = df["cleaned_headline"].apply(lambda x: sia.polarity_scores(x)["neg"])
    df["neu"] = df["cleaned_headline"].apply(lambda x: sia.polarity_scores(x)["neu"])
    df["pos"] = df["cleaned_headline"].apply(lambda x: sia.polarity_scores(x)["pos"])
    df["compound"] = df["sentiment_score"]
    return df

# Clustering
def add_clusters(df, num_clusters=5):
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(df["cleaned_headline"])
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X)
    return df

# Full Pipeline
df = fetch_data()
if df is not None:
    df = add_sentiment(df)
    df = add_clusters(df)
    



# --- Load dataset ---
@st.cache_data
def load_data():
      # Ensure correct path
    df["date"] = pd.to_datetime(df["date"])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    return df

df = load_data()

# --- Preprocess Data ---
sentiment_trend = df.groupby(["year", "category"])[["compound"]].mean().reset_index()
years = sorted(sentiment_trend["year"].unique())

# --- Sidebar Navigation ---
st.sidebar.title(" Navigation")
page = st.sidebar.radio("Go to", ["Score by Year", "Score by category over time", "Year +2", "one year"])

# --- Home Page ---
if page == "Score by Year":
    st.title("Sentiment score by year")
    # st.subheader("📈 Sentiment Trends Over Time")

    fig1 = px.line(
        sentiment_trend,
        x="category",
        y="compound",
        color="year",
        markers=True,
        title="Sentiment Score by Year",
        labels={"compound": "Average Sentiment Score", "category": "News Category"}
    )
    st.plotly_chart(fig1)

# --- Sentiment Analysis Page ---
elif page == "Score by category over time":
    # st.title("📊 Sentiment Analysis")

    st.subheader("Sentiment Score by Category Over Time")

    fig12 = px.bar(
        sentiment_trend, x="category", y="compound", color="category",
        animation_frame="year", animation_group="category", range_y=[-1, 1],
        title="Sentiment Score by Category Over Time",
        labels={"compound": "Average Sentiment Score", "category": "News Category"}
    )

    fig12.update_layout(
        xaxis_title="News Category",
        yaxis_title="Average Sentiment Score",
        title_x=0.5,
        showlegend=True
    )

    st.plotly_chart(fig12)

# --- Trends Page ---
elif page == "Year +2":
    st.title(" Sentiment Trends Over Time")

    st.write("Select a year to view sentiment trends across different categories.")

    # Define range for years above & below selection
    top_bottom_years = 2  

    # Dropdown selection for year
    selected_year = st.selectbox("Select a Year:", years, index=len(years) - 1)

    # Determine visible years (selected year ± top_bottom_years)
    visible_years = list(range(max(years[0], selected_year - top_bottom_years),
                               min(years[-1] + 1, selected_year + top_bottom_years + 1)))

    # --- Create figure ---
    fig = go.Figure()

    # Add traces for each visible year
    for year in visible_years:
        df_year = sentiment_trend[sentiment_trend["year"] == year]
        fig.add_trace(go.Scatter(
            x=df_year["category"], 
            y=df_year["compound"],
            mode='lines+markers', 
            name=str(year),
            visible=True  # Show only selected range of years
        ))

    # Update layout
    fig.update_layout(
        title=f"Sentiment Score by Year & Category ({selected_year} ± {top_bottom_years} Years)",
        xaxis_title="News Category",
        yaxis_title="Average Sentiment Score",
        showlegend=True
    )

    st.plotly_chart(fig)

elif page == "one year":
    st.title(" Sentiment Trends Over Time")

    st.write("Select a year to view sentiment trends across different categories.")

    # --- Create dropdown-based interactive plot ---
    fig = go.Figure()

    # Add traces for each year
    for i, year in enumerate(years):
        df_year = sentiment_trend[sentiment_trend["year"] == year]
        fig.add_trace(go.Scatter(
            x=df_year["category"], 
            y=df_year["compound"],
            mode='lines+markers', 
            name=str(year),
            visible=(i == 0)  # Show only the first year's data initially
        ))

    # Create dropdown menu
    year_dropdown = [
        dict(
            method='update',
            args=[{'visible': [y == year for y in years]},
                  {'title': f'Sentiment Score by Year: {year}'}],
            label=str(year)
        ) for year in years
    ]

    # Update layout with dropdown
    fig.update_layout(
        title="Sentiment Score by Year & Category",
        xaxis_title="News Category",
        yaxis_title="Average Sentiment Score",
        updatemenus=[dict(
            buttons=year_dropdown,
            direction='down',
            x=0.1, xanchor='left', y=1.1, yanchor='top'
        )]
    )

    st.plotly_chart(fig)

# # --- About Page ---
# elif page == "About":
#     st.title("ℹ️ About This Project")
#     st.write("**Senticonomy** is a news sentiment analysis platform that visualizes economic impacts.")
