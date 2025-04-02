import React from 'react'

export default function Home() {
  return (
    <div className="space-y-8">
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
            Current Leaders
          </h2>
          
          <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
            {/* Eastern Conference */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-4">Eastern Conference</h3>
              <div className="space-y-4">
                <div className="bg-white p-4 rounded-md shadow">
                  <div className="text-sm text-gray-500">Current Player of the Month</div>
                  <div className="text-lg font-medium">Loading...</div>
                </div>
                <div className="bg-white p-4 rounded-md shadow">
                  <div className="text-sm text-gray-500">Current Player of the Week</div>
                  <div className="text-lg font-medium">Loading...</div>
                </div>
              </div>
            </div>

            {/* Western Conference */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-4">Western Conference</h3>
              <div className="space-y-4">
                <div className="bg-white p-4 rounded-md shadow">
                  <div className="text-sm text-gray-500">Current Player of the Month</div>
                  <div className="text-lg font-medium">Loading...</div>
                </div>
                <div className="bg-white p-4 rounded-md shadow">
                  <div className="text-sm text-gray-500">Current Player of the Week</div>
                  <div className="text-lg font-medium">Loading...</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Stats Leaders */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-xl font-semibold mb-6">Recent Stats Leaders</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Points</div>
              <div className="text-lg font-medium">Loading...</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Rebounds</div>
              <div className="text-lg font-medium">Loading...</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Assists</div>
              <div className="text-lg font-medium">Loading...</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Efficiency</div>
              <div className="text-lg font-medium">Loading...</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 