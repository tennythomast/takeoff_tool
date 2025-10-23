export default function UsageAndCredits() {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-6">Usage & Credits</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border rounded-lg p-6 shadow">
            <h3 className="text-lg font-semibold mb-4">This Month's Usage</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>AI Requests:</span>
                <span className="font-medium">47,832</span>
              </div>
              <div className="flex justify-between">
                <span>Optimized Spend:</span>
                <span className="font-medium">$1,247</span>
              </div>
              <div className="flex justify-between">
                <span>Savings Generated:</span>
                <span className="font-medium text-green-600">$2,841</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white border rounded-lg p-6 shadow">
            <h3 className="text-lg font-semibold mb-4">Plan Limits</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Monthly Spend Limit:</span>
                <span className="font-medium">$2,500</span>
              </div>
              <div className="flex justify-between">
                <span>Used:</span>
                <span className="font-medium">49.9%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{width: '49.9%'}}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
  