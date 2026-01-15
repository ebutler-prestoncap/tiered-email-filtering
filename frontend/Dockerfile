FROM node:18-alpine

WORKDIR /app

# Copy package.json only (not package-lock.json to avoid platform mismatch)
COPY package.json ./

# Install dependencies (generates fresh lock file for Alpine)
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host"]

