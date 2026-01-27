FROM node:22-alpine

WORKDIR /app

# Build args for environment variables (Vite embeds at build time)
ARG VITE_GEMINI_API_KEY
ENV VITE_GEMINI_API_KEY=$VITE_GEMINI_API_KEY

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