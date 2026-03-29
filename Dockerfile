# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copiem tot repo-ul
COPY . /app

# Instalăm dependințele
RUN pip install --no-cache-dir \
    streamlit \
    pandas \
    requests \
    redis \
    streamlit-autorefresh

# Expunem portul Streamlit
EXPOSE 8501

# Comanda de start
CMD ["streamlit", "run", "scanner.py", "--server.port=8501", "--server.address=0.0.0.0"]
