FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy application files
COPY . .

# Set environment variables
ENV NODE_ENV=development
ENV PORT=3000

# Expose the port
EXPOSE 3000

# Start the application in development mode
CMD ["npm", "start"] 