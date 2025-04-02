import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';
import { getPlayerStats, calculateEfficiency } from '../../../lib/nba-api';
import { subDays, startOfDay, endOfDay } from 'date-fns';

const prisma = new PrismaClient();

export async function GET() {
  try {
    // Get yesterday's stats
    const yesterday = subDays(new Date(), 1);
    const startDate = startOfDay(yesterday);
    const endDate = endOfDay(yesterday);

    const stats = await getPlayerStats(startDate, endDate);

    // Process each player's stats
    for (const stat of stats) {
      const efficiency = calculateEfficiency(stat);

      // Update or create player
      const player = await prisma.player.upsert({
        where: { id: String(stat.player.id) },
        create: {
          id: String(stat.player.id),
          name: `${stat.player.first_name} ${stat.player.last_name}`,
          team: stat.player.team.full_name,
          position: stat.player.position,
        },
        update: {
          team: stat.player.team.full_name,
          position: stat.player.position,
        },
      });

      // Add stats for the day
      await prisma.playerStats.create({
        data: {
          playerId: player.id,
          date: startDate,
          points: stat.pts,
          rebounds: stat.reb,
          assists: stat.ast,
          steals: stat.stl,
          blocks: stat.blk,
          fieldGoalPct: stat.fg_pct,
          threePointPct: stat.fg3_pct,
          freeThrowPct: stat.ft_pct,
          minutesPlayed: parseFloat(stat.min || '0'),
          gamesPlayed: stat.games_played,
          plusMinus: stat.plus_minus,
          efficiency,
        },
      });
    }

    // Update awards if it's the end of week/month
    await updateAwards(startDate);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error updating stats:', error);
    return NextResponse.json({ error: 'Failed to update stats' }, { status: 500 });
  }
}

async function updateAwards(date: Date) {
  // Weekly awards logic
  const isEndOfWeek = date.getDay() === 0; // Sunday
  if (isEndOfWeek) {
    const weekStart = subDays(date, 6);
    const weekStats = await prisma.playerStats.findMany({
      where: {
        date: {
          gte: weekStart,
          lte: date,
        },
      },
      include: {
        player: true,
      },
    });

    // Group by conference and find top performers
    const conferenceStats = {
      Eastern: weekStats.filter(stat => stat.player.team.includes('East')),
      Western: weekStats.filter(stat => stat.player.team.includes('West')),
    };

    for (const [conference, stats] of Object.entries(conferenceStats)) {
      if (stats.length > 0) {
        const topPerformer = stats.reduce((a, b) => 
          a.efficiency > b.efficiency ? a : b
        );

        await prisma.weeklyAward.create({
          data: {
            playerId: topPerformer.playerId,
            weekStart,
            weekEnd: date,
            conference,
          },
        });
      }
    }
  }

  // Monthly awards logic
  const isEndOfMonth = new Date(date.getTime()).getDate() === new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  if (isEndOfMonth) {
    const monthStats = await prisma.playerStats.findMany({
      where: {
        date: {
          gte: new Date(date.getFullYear(), date.getMonth(), 1),
          lte: date,
        },
      },
      include: {
        player: true,
      },
    });

    const conferenceStats = {
      Eastern: monthStats.filter(stat => stat.player.team.includes('East')),
      Western: monthStats.filter(stat => stat.player.team.includes('West')),
    };

    for (const [conference, stats] of Object.entries(conferenceStats)) {
      if (stats.length > 0) {
        const topPerformer = stats.reduce((a, b) => 
          a.efficiency > b.efficiency ? a : b
        );

        await prisma.monthlyAward.create({
          data: {
            playerId: topPerformer.playerId,
            month: date.getMonth() + 1,
            year: date.getFullYear(),
            conference,
          },
        });
      }
    }
  }
} 