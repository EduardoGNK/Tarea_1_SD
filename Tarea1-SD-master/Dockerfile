FROM python:3.10-slim


RUN apt-get update && \
    apt-get install -y wget unzip gnupg curl chromium-driver chromium && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


ENV BROWSER_PATH=/usr/bin/chromium
ENV PATH="${PATH}:/usr/bin"


WORKDIR /application


COPY . .

RUN pip install --no-cache-dir \
    pymongo \
    redis \
    requests \
    matplotlib \
    folium \
    pandas \
    seaborn


CMD ["python", "data_collector.py"]