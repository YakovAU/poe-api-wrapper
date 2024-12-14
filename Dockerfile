FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8091

RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
CMD ["python", "-m", "poe_api_wrapper.openai.api"]
