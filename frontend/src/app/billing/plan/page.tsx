export default function CurrentPlan() {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-6">Current Plan</h1>
        <div className="bg-white border rounded-lg p-6 shadow">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Professional Plan</h2>
            <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
              Active
            </span>
          </div>
          <p className="text-gray-600 mb-4">
            Optimize up to $2,500 AI spend per month with advanced routing and analytics.
          </p>
          <div className="text-2xl font-bold text-gray-900">$299/month</div>
        </div>
      </div>
    );
  }