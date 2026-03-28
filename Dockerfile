# Dockerfile
FROM python:3.10

# Setăm directorul de lucru în container
WORKDIR /app

# Copiem fișierele repo în container
COPY . /app

# Instalăm dependențele
RUN pip install --no-cache-dir streamlit yfinance pandas requests streamlit-autorefresh

# Expunem portul Streamlit
EXPOSE 8501

# Comanda default pentru a porni aplicația
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
