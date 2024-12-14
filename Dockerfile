FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8091

CMD ["python", "-m", "poe_api_wrapper.openai.api"]
