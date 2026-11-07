FROM python:3-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOST=0.0.0.0 PORT=8790 TESSERACT_CMD=/usr/bin/tesseract TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
COPY requirements-doc-ai.txt ./
RUN pip install --no-cache-dir -r requirements-doc-ai.txt
COPY serwer/ serwer/
COPY mockup/ mockup/
RUN useradd --create-home --uid 10001 mobywatel && chown -R mobywatel /app
USER mobywatel
EXPOSE 8790
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python3 -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8790'),timeout=4)"
CMD ["python3", "serwer/server.py"]
