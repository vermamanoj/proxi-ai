FROM node:22-alpine

WORKDIR /app

# Copy package definitions first for better caching
COPY package.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Expose the standard Vite port
EXPOSE 5173

# Start the development server
# The --host flag is crucial for Docker networking
CMD ["npm", "run", "dev", "--", "--host"]