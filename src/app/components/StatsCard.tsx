import React from 'react';
import type { PlayerStats } from '../lib/nba-api';

interface StatsCardProps {
  title: string;
  stats: PlayerStats[];
  statKey: keyof PlayerStats;
  loading?: boolean;
}

export default function StatsCard({ title, stats, statKey, loading = false }: StatsCardProps) {
  if (loading) {
    return (
      <div className="bg-gray-50 p-4 rounded-lg animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-1/2 mb-4"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 p-4 rounded-lg">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="space-y-2">
        {stats.map((stat, index) => (
          <div key={index} className="flex justify-between items-center">
            <div className="flex items-center">
              <span className="text-sm font-medium">
                {stat.player.first_name} {stat.player.last_name}
              </span>
              <span className="text-xs text-gray-500 ml-2">
                {stat.player.team.full_name}
              </span>
            </div>
            <span className="text-sm font-semibold">
              {typeof stat[statKey] === 'number' 
                ? (stat[statKey] as number).toFixed(1) 
                : stat[statKey]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
} 