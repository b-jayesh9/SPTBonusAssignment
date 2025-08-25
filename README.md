# Amazon Product Data Analysis Application

## Overview

This application provides a high-performance, interactive web interface for analyzing the Amazon UK Products Dataset.
It is designed for both guided analysis and ad-hoc data exploration, offering two main functionalities:

1.  **Automated Analysis:** A dashboard with pre-built reports for category performance, rating variability, and statistical significance (Z-score).
2.  **SQL Explorer:** A direct SQL interface for technical users to perform custom queries against the dataset.

The entire system is containerized with Docker and designed with scalability and efficiency as primary objectives.

---

## Instructions for Execution

### Prerequisites

-   **Docker:** The Docker engine must be installed and running on your system.

### Environment Setup and Execution Steps

The application is run as a Docker container, ensuring a consistent and reproducible environment.

**Step 1: Build the Docker Image**

This command builds the application image from the `Dockerfile`. This step is only required once, or whenever application code is changed. It does **not** download the dataset.

```bash
docker build -t sql-query-ui .   
```

**Step 2: Run the Docker Container**

This command starts the application. On its first launch, it will download the dataset and store it in a persistent volume.

Execute the following command, replacing `"your_username"` and `"your_key"` with your Kaggle API credentials:

```bash
docker run --rm -p 8501:8501 \
  -v amz-data:/app/data \
  sql-query-ui
```

**Command Breakdown:**
-   `--rm`: Automatically removes the container when it is stopped, keeping the system clean.
-   `-p 8501:8501`: Maps port 8501 from the container to port 8501 on your local machine.
-   `-v amz-data:/app/data`: Creates a named Docker Volume called `amz-data` and mounts it to the `/app/data` directory inside the container. This ensures the downloaded dataset persists between container runs.

**Behavior on First Run:** The container will first download and unzip the dataset into the `amz-data` volume. This may take several minutes.

**Behavior on Subsequent Runs:** The container will detect the dataset in the volume and start the application almost instantly, bypassing the download.

**Step 3: Access the Application**

Open a web browser and navigate to:
`http://localhost:8501`

---

## Key Design Decisions and Scalability

The analysis pipeline was designed to be efficient and scalable, making it suitable for integration into a larger dashboard or future API service.

### 1. Data Processing Engine: DuckDB

-   **Decision:** DuckDB was chosen as the in-process analytical database engine for all data manipulation and querying.
-   **Rationale & Scalability:**
    -   **Performance:** DuckDB is a columnar-vectorized database optimized for analytical (OLAP) queries like aggregations and calculations, which are central to this project. It is significantly faster than row-based databases or general-purpose libraries like Pandas for these tasks on large datasets.
    -   **Resource Efficiency:** As an in-process library, it runs within the Python application, eliminating the overhead of a separate database server. It can efficiently query data directly from disk and is optimized to handle datasets larger than available RAM.
    -   **Push-down Execution:** All complex calculations (e.g., standard deviation, Z-score) are executed as single SQL queries entirely within DuckDB. This "push-down" approach is highly scalable as it minimizes data transfer between the database engine and the Python application layer.

### 2. Scalable Architecture: Decoupled Data and Application

-   **Decision:** The dataset is downloaded at runtime and stored in a persistent Docker Volume, rather than being included in the Docker image.
-   **Rationale & Scalability:**
    -   **Smaller, Portable Images:** The Docker image contains only the application code, resulting in a much smaller footprint (~500MB vs. ~1.5GB+). This makes the image faster to build, push, and pull from registries.
    -   **Data Independence:** The data's lifecycle is independent of the application. The application can be updated and redeployed without affecting the stored data. For a much larger dataset, this volume could be an NFS mount or a connection to a cloud object store (like S3), and the core application logic would remain unchanged.
    -   **Efficient Development:** Developers can rebuild the image to reflect code changes in seconds, without re-downloading the data on every build.

### 3. Caching Strategy for Dashboard Performance

-   **Decision:** Streamlit's caching mechanisms (`@st.cache_resource` and `@st.cache_data`) are used strategically.
-   **Rationale & Scalability:**
    -   `@st.cache_resource` is used for the DuckDB connection. This ensures the database is initialized and the large dataset is loaded into memory only once, on the first user's first visit. All subsequent users and sessions share this single, resource-intensive object.
    -   `@st.cache_data` is used for the results of each analytical function. If multiple users request the same "Rating Variability Analysis," the expensive SQL query is run only once. All subsequent requests receive the cached result instantly. This dramatically improves performance and reduces database load in a multi-user dashboard environment.

### 4. Containerization and Future Integration

-   **Decision:** The entire application is containerized using Docker.
-   **Rationale & Scalability:**
    -   **Reproducibility:** Docker guarantees a consistent environment, eliminating issues related to dependencies or operating system differences.
    -   **API Integration:** The core analytical functions (e.g., `perform_zscore_analysis`) are decoupled from the Streamlit UI. This modular design makes it straightforward to expose this same logic via a REST API framework (like FastAPI or Flask) in the future. The same scalable, containerized backend could serve both the interactive dashboard and a programmatic API endpoint.