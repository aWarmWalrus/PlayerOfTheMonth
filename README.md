# NBA Player of the Month/Week Tracker

A modern web application that tracks and displays NBA Player of the Month and Player of the Week awards, updating daily with the latest game statistics and performances.

## Features

- 📊 Daily updated leaderboard for Player of the Month and Player of the Week candidates
- 🏀 Comprehensive player statistics and performance metrics
- 📅 Daily updates incorporating the previous night's games
- 📱 Responsive design for all devices
- 🔍 Interactive filtering and sorting capabilities
- 📈 Historical data tracking and visualization

## Tech Stack

- Next.js 14 with App Router
- TypeScript
- Tailwind CSS
- Web scraping of basketball-reference.com
- Prisma with PostgreSQL
- Python for web scraping scripts
- Node.js Cron Jobs for Daily Updates

## Data Pipeline

- Python scripts scrape data from basketball-reference.com.
- The scraped data is processed.
- Processed data is stored in the PostgreSQL database using Prisma.

## Getting Started

1. Clone the repository

### Backend (Data Scraping)

1. Navigate to the project root directory (where `requirements.txt` is located).
2. Set up a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (Python scripts in the `scripts/` directory are typically run from the project root after activating the virtual environment.)

### Frontend (Web Application)

1. Install Node.js dependencies:
   ```bash
   npm install
   ```
2. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```
   (Update `.env.local` with your actual database URL and any other necessary configurations)
3. Set up the database:
   ```bash
   bash scripts/setup-db.sh
   ```
4. Run the development server:
   ```bash
   npm run dev
   ```

## Environment Variables

Create a `.env.local` file with the following variable:
```
DATABASE_URL="postgresql://user:password@localhost:5432/mydatabase?schema=public"
```
Make sure to replace `user`, `password`, `localhost`, `5432`, and `mydatabase` with your actual PostgreSQL connection details. The `?schema=public` part is often standard but might need adjustment based on your database setup.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License