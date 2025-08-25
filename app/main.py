import streamlit as st
import duckdb
import os
import logging

# --- Logger Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Amazon UK Product Analysis",
    layout="wide",
)

# --- Constants ---
DATA_FILE_PATH = os.getenv("DATA_FILE_PATH", "/app/data/amz_uk_processed_data.csv")
TABLE_NAME = "products"


# --- Caching the DuckDB Connection and Data Loading ---
@st.cache_resource
def get_duckdb_connection():
    """Establishes a DuckDB connection and loads the dataset into a table."""
    try:
        logging.info("Initializing DuckDB connection and loading data...")
        if not os.path.exists(DATA_FILE_PATH):
            st.error(f"Data file not found at the specified path: {DATA_FILE_PATH}.")
            logging.error(f"Data file not found at {DATA_FILE_PATH}.")
            st.stop()

        con = duckdb.connect(database=':memory:', read_only=False)
        con.execute(f"""
            CREATE TABLE {TABLE_NAME} AS 
            SELECT *,
                CAST("stars" AS FLOAT) AS rating
            FROM read_csv_auto('{DATA_FILE_PATH}');
        """)
        logging.info("DuckDB connection successful and data loaded into table '%s'.", TABLE_NAME)
        return con
    except Exception as e:
        logging.error("Failed to initialize the database connection.", exc_info=True)
        st.error(f"Failed to initialize the database connection: {e}")
        st.stop()


# --- Analytical Functions ---
@st.cache_data
def perform_variability_analysis(_con):
    """Calculates rating variability statistics for each product category."""
    query = f"""
    SELECT
        "categoryName" AS category,
        COUNT(*) AS number_of_products,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(STDDEV_SAMP(rating), 2) AS std_dev_rating,
        ROUND(VAR_SAMP(rating), 2) AS variance_rating
    FROM {TABLE_NAME}
    WHERE rating IS NOT NULL AND rating > 0
    GROUP BY category
    HAVING COUNT(*) > 10
    ORDER BY std_dev_rating DESC;
    """
    return _con.execute(query).fetchdf()


@st.cache_data
def perform_zscore_analysis(_con):
    """Calculates the Z-score for each category's average rating against the overall mean."""
    query = f"""
    WITH category_stats AS (
        SELECT
            "categoryName" AS category,
            COUNT(*) as number_of_products,
            AVG(rating) AS avg_rating
        FROM {TABLE_NAME}
        WHERE rating IS NOT NULL AND rating > 0
        GROUP BY category
        HAVING number_of_products > 10
    ),
    overall_stats AS (
        SELECT
            AVG(rating) AS overall_avg_rating,
            STDDEV_SAMP(rating) AS overall_std_dev_rating
        FROM {TABLE_NAME}
        WHERE rating IS NOT NULL AND rating > 0
    )
    SELECT
        cs.category,
        cs.number_of_products,
        ROUND(cs.avg_rating, 2) AS avg_rating,
        ROUND(
            (cs.avg_rating - os.overall_avg_rating) / NULLIF(os.overall_std_dev_rating, 0), 
            2
        ) AS z_score
    FROM category_stats cs, overall_stats os
    ORDER BY z_score DESC;
    """
    return _con.execute(query).fetchdf()


# --- Initialize Connection ---
con = get_duckdb_connection()

# --- Main Application UI ---
st.title("Amazon UK Product Data Analysis")

tab1, tab2 = st.tabs(["Automated Analysis", "SQL Explorer"])

with tab1:
    st.header("Pre-built Analytical Reports")
    st.markdown("Select a report for automated analysis of the dataset.")
    analysis_options = {
        "Select a Report": lambda: None,
        "Rating Variability Analysis": perform_variability_analysis,
        "Category Performance (Z-Score)": perform_zscore_analysis,  # Changed label for clarity
    }
    selected_analysis = st.selectbox("Select an analysis:", options=list(analysis_options.keys()),
                                     label_visibility="collapsed")

    if selected_analysis != "Select a Report":
        logging.info("User selected analysis: '%s'", selected_analysis)
        try:
            with st.spinner("Executing analysis..."):
                analysis_function = analysis_options[selected_analysis]
                results_df = analysis_function(con)
            st.success("Analysis complete.")

            if selected_analysis == "Rating Variability Analysis":
                st.subheader("Rating Variability by Category")
                st.markdown(
                    "This report assesses the consistency of product ratings within each category. A high standard deviation implies greater variability in customer ratings.")
                st.markdown("---")
                st.markdown("#### Categories with Highest Rating Variability")
                st.dataframe(results_df.head(10), use_container_width=True)
                st.markdown("#### Categories with Lowest Rating Variability")
                st.dataframe(results_df.sort_values(by="std_dev_rating", ascending=True).head(10),
                             use_container_width=True)

            elif selected_analysis == "Category Performance (Z-Score)":
                st.subheader("Category Ratings vs. Dataset Average (Z-Score Analysis)")
                st.markdown(
                    "This analysis identifies categories whose average rating deviates from the overall dataset average. The Z-score measures a category's deviation from the mean in terms of standard deviations.")
                st.markdown("---")
                st.markdown("#### Top Overall Category Rankings (by Z-score)")
                st.dataframe(results_df.head(10), use_container_width=True)
                st.markdown("#### Bottom Overall Category Rankings (by Z-score)")
                st.dataframe(results_df.tail(10).sort_values(by="z_score", ascending=True), use_container_width=True)
                st.markdown("---")

                # --- NEW DYNAMIC THRESHOLD LOGIC ---
                st.markdown("### Top/Bottom Performing Categories (Relative Z-score)")
                st.markdown(
                    """
                    Instead of a fixed statistical threshold, this section identifies categories whose Z-scores fall into the extreme percentiles of the Z-score distribution.
                    This provides a data-driven, relative measure of performance compared to other categories in the dataset.
                    """
                )

                # Calculate dynamic thresholds using percentiles
                # We need to handle potential NaN values in Z-score if there was division by zero
                # or very little variance.
                valid_z_scores = results_df['z_score'].dropna()

                if not valid_z_scores.empty:
                    # Define percentiles for top and bottom (e.g., 90th percentile and 10th percentile)
                    high_threshold = valid_z_scores.quantile(0.90)
                    low_threshold = valid_z_scores.quantile(0.10)

                    st.info(
                        f"Dynamically identified thresholds: Top 10% of categories have Z-score > {high_threshold:.2f}, Bottom 10% have Z-score < {low_threshold:.2f}.")

                    top_performers = results_df[results_df['z_score'] >= high_threshold].sort_values(by='z_score',
                                                                                                     ascending=False)
                    bottom_performers = results_df[results_df['z_score'] <= low_threshold].sort_values(by='z_score',
                                                                                                       ascending=True)

                    st.markdown(f"#### Top Performing Categories (Z-score >= {high_threshold:.2f} - Approx. Top 10%)")
                    if top_performers.empty:
                        st.info("No categories met the dynamic high-performance threshold.")
                    else:
                        st.dataframe(top_performers, use_container_width=True)

                    st.markdown(
                        f"#### Bottom Performing Categories (Z-score <= {low_threshold:.2f} - Approx. Bottom 10%)")
                    if bottom_performers.empty:
                        st.info("No categories met the dynamic low-performance threshold.")
                    else:
                        st.dataframe(bottom_performers, use_container_width=True)
                else:
                    st.warning(
                        "Could not calculate dynamic thresholds: Z-score data is not available or has no variance.")

                st.markdown("---")
                st.markdown(
                    """
                    **Note on Statistical Significance (Traditional View):**
                    For context, a traditional statistical significance threshold (at 95% confidence) is a Z-score greater than 1.96 or less than -1.96.
                    These fixed thresholds are typically used when inferring properties of a larger population from a sample.
                    """
                )

                high_signif_performers = results_df[results_df['z_score'] > 1.96]
                low_signif_performers = results_df[results_df['z_score'] < -1.96]

                st.markdown("#### Traditional Statistically Significant High-Performers (Z-score > 1.96)")
                if high_signif_performers.empty:
                    st.info(
                        "No categories met the traditional statistical significance threshold for high performance (Z-score > 1.96).")
                else:
                    st.dataframe(high_signif_performers, use_container_width=True)

                st.markdown("#### Traditional Statistically Significant Low-Performers (Z-score < -1.96)")
                if low_signif_performers.empty:
                    st.info(
                        "No categories met the traditional statistical significance threshold for low performance (Z-score < -1.96).")
                else:
                    st.dataframe(low_signif_performers.sort_values(by="z_score", ascending=True),
                                 use_container_width=True)

            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(label=f"Download Full '{selected_analysis}' Report", data=csv,
                               file_name=f"{selected_analysis.lower().replace(' ', '_')}_report.csv", mime='text/csv')
        except Exception as e:
            logging.error("An error occurred during analysis: %s", selected_analysis, exc_info=True)
            st.error(f"An error occurred during the analysis: {e}")

with tab2:
    st.header("Interactive SQL Query Editor")
    st.info(
        f"The dataset is loaded into a table named `{TABLE_NAME}`. Enter a SQL query below and select 'Execute Query'.")
    default_query = f"SELECT * FROM {TABLE_NAME} LIMIT 10;"
    query_text = st.text_area("SQL Query:", value=default_query, height=300, label_visibility="collapsed")
    if st.button("Execute Query"):
        if query_text:
            logging.info("Executing user-provided SQL query.")
            try:
                with st.spinner("Executing query..."):
                    results_df = con.execute(query_text).fetchdf()
                st.success("Query executed successfully.")
                st.dataframe(results_df, use_container_width=True, height=500)
                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Download Results as CSV", data=csv, file_name='query_results.csv',
                                   mime='text/csv')
            except Exception as e:
                logging.error("An error occurred during query execution.", exc_info=True)
                st.error(f"An error occurred during query execution: {e}")
        else:
            st.warning("Please enter a SQL query to execute.")