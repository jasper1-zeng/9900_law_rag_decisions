FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the port
EXPOSE 5001

# Update the CMD to use environment variables with default values
CMD python app.py --uri ${NEO4J_URI} --user ${NEO4J_USER} --password ${NEO4J_PASSWORD} --port ${PORT:-5001} --host 0.0.0.0 