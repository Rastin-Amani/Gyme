# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /code

# Copy requirements directly from the app folder
COPY ./app/requirements.txt .

# Install using the Liara mirror to bypass network blocks
RUN pip install --no-cache-dir --index-url https://package-mirror.liara.ir/repository/pypi/simple -r requirements.txt

# Copy the entire app folder
COPY ./app ./app

# Add this line to copy your data folder into the container!
COPY ./data ./data

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]