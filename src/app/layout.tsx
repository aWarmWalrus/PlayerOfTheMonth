import React from 'react'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'NBA Player of the Month/Week Tracker',
  description: 'Track NBA Player of the Month and Week awards with real-time statistics and updates.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="h-full bg-gray-50">
      <body className={`${inter.className} h-full`}>
        <div className="min-h-full">
          <nav className="bg-indigo-600">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="flex h-16 items-center justify-between">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <h1 className="text-white text-xl font-bold">NBA Awards Tracker</h1>
                  </div>
                  <div className="hidden md:block">
                    <div className="ml-10 flex items-baseline space-x-4">
                      <a href="/" className="text-white hover:bg-indigo-500 hover:bg-opacity-75 rounded-md px-3 py-2">
                        Dashboard
                      </a>
                      <a href="/monthly" className="text-white hover:bg-indigo-500 hover:bg-opacity-75 rounded-md px-3 py-2">
                        Monthly Awards
                      </a>
                      <a href="/weekly" className="text-white hover:bg-indigo-500 hover:bg-opacity-75 rounded-md px-3 py-2">
                        Weekly Awards
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          <main>
            <div className="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  )
} 