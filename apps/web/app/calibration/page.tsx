"use client"

import { useEffect, useState } from "react"

export default function CalibrationPage() {
  const [units, setUnits] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/calibration/units`)
      .then((res) => res.json())
      .then((data) => {
        setUnits(data || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error("Failed to fetch calibration units:", err)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return <div className="p-8 text-gray-500">加载中...</div>
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">M3 概率校准单元</h1>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          onClick={() => alert("功能开发中: 重新计算所有单元")}
        >
          全量重新计算
        </button>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类别 & 价格桶</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时间桶 & 流动性</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">样本量</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">期望边缘</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">置信区间 (95%)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {units.length > 0 ? units.map((unit) => (
              <tr key={unit.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{unit.category_code}</div>
                  <div className="text-sm text-gray-500">Bucket: {unit.price_bucket}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{unit.time_bucket}</div>
                  <div className="text-sm text-gray-500">{unit.liquidity_tier} / {unit.window_type}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {unit.sample_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-indigo-600">
                  {(unit.edge_estimate * 100).toFixed(2)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  [{(unit.interval_low * 100).toFixed(2)}%, {(unit.interval_high * 100).toFixed(2)}%]
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    unit.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                  }`}>
                    {unit.is_active ? "Active" : "Disabled"}
                  </span>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={6} className="px-6 py-10 text-center text-gray-500 italic">
                  暂无校准单元数据，请触发计算或检查数据源。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
