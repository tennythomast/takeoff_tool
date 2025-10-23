"use client";

export default function SavingsReport() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Savings Report</h1>
      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-green-800 mb-4">Cost Optimization Results</h2>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span>Mixtral Local vs GPT-4:</span>
            <span className="font-bold text-green-600">95% savings</span>
          </div>
          <div className="flex justify-between">
            <span>Smart Routing vs Direct API:</span>
            <span className="font-bold text-green-600">67% savings</span>
          </div>
          <div className="flex justify-between">
            <span>Total Monthly Savings:</span>
            <span className="font-bold text-green-600">$2,841</span>
          </div>
        </div>
      </div>
    </div>
  );
}
