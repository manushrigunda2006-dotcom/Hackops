FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

# Dev server for now. Swap to a static build served by nginx once the
# app is stable, if we want a leaner production image before submission.
CMD ["npm", "run", "dev"]
