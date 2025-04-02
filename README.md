# NBA Player of the Month/Week Tracker

A modern web application that tracks and displays NBA Player of the Month and Player of the Week awards, updating daily with the latest game statistics and performances.

## Features

- 📊 Real-time leaderboard for Player of the Month and Player of the Week candidates
- 🏀 Comprehensive player statistics and performance metrics
- 📅 Daily updates incorporating the previous night's games
- 📱 Responsive design for all devices
- 🔍 Interactive filtering and sorting capabilities
- 📈 Historical data tracking and visualization

## Tech Stack

- Next.js 14 with App Router
- TypeScript
- Tailwind CSS
- NBA API Integration
- Prisma with PostgreSQL
- Node.js Cron Jobs for Daily Updates

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```
4. Run the development server:
   ```bash
   npm run dev
   ```

## Environment Variables

Create a `.env.local` file with the following variables:
```
DATABASE_URL="postgresql://..."
NBA_API_KEY="your-api-key"
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License