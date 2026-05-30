# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /code

# Copy requirements directly from the app folder and install them
COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app folder (This automatically includes your static folder!)
COPY ./app ./app

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]