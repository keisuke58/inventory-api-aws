import { useEffect, useState } from "react";
import axios from "axios";

export default function App() {
  const [stocks, setStocks] = useState<Record<string, number>>({});

  const fetchStocks = async () => {
    const res = await axios.get("/v1/stocks");
    setStocks(res.data);
  };

  const addStock = async () => {
    await axios.post("/v1/stocks", { name: "demo", amount: 1 });
    fetchStocks();
  };

  useEffect(() => {
    fetchStocks();
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-2">Inventory Dashboard</h1>
      <button
        className="px-3 py-1 bg-blue-600 text-white rounded"
        onClick={addStock}
      >
        + Add demo
      </button>
      <ul className="mt-4 space-y-1">
        {Object.entries(stocks).map(([k, v]) => (
          <li key={k}>
            {k}: {v}
          </li>
        ))}
      </ul>
    </div>
  );
}