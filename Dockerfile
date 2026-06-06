# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /code

# Copy the local packages folder into the image
COPY ./packages ./packages

# Copy requirements file
COPY ./app/requirements.txt .

# Install ONLY from the local folder, ignore the internet
RUN pip install --no-index --find-links=./packages -r requirements.txt

# Copy the entire app folder
COPY ./app ./app

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]