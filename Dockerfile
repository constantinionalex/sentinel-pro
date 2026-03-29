FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt \
    streamlit \
    pandas \
    numpy \
    yfinance \
    redis \
    requests \
    aiohttp \
    streamlit-autorefresh

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
