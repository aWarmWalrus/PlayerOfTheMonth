#!/bin/bash

# Create the database
psql -U postgres -c "CREATE DATABASE nba_tracker;"

# Run Prisma migrations
npx prisma migrate dev

# Generate Prisma client
npx prisma generate 