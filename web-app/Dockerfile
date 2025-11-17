FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy app
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
