FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Use a lightweight server to serve the built app
RUN npm install -g serve
CMD ["serve", "-s", "build", "-l", "3000"]
