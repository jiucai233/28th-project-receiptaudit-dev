/**
 * Data Editor Component
 * Equivalent to web/src/components/data_editor_component.py
 */

import { useState, useEffect, useRef } from 'react';
import { PenLine, Plus, Trash2, Lightbulb, ShoppingCart } from 'lucide-react';
import type { ReceiptData, ReceiptItem } from '@/types';

interface DataEditorProps {
  data: ReceiptData;
  onChange: (data: ReceiptData) => void;
}

export const DataEditor: React.FC<DataEditorProps> = ({ data, onChange }) => {
  const [storeName, setStoreName] = useState(data.store_name);
  const [date, setDate] = useState(data.date);
  const [items, setItems] = useState<ReceiptItem[]>(data.items);

  // 다른 영수증 선택 시 내부 상태 재초기화
  const prevReceiptId = useRef(data.receipt_id);
  useEffect(() => {
    if (data.receipt_id !== prevReceiptId.current) {
      prevReceiptId.current = data.receipt_id;
      setStoreName(data.store_name);
      setDate(data.date);
      setItems(data.items);
    }
  }, [data.receipt_id, data.store_name, data.date, data.items]);

  // Update parent when local state changes
  useEffect(() => {
    const totalPrice = items.reduce((sum, item) => sum + item.price, 0);
    onChange({
      ...data,
      store_name: storeName,
      date,
      items,
      total_price: totalPrice,
    });
  }, [storeName, date, items]);

  const handleItemChange = (id: number, field: keyof ReceiptItem, value: string | number) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;

        const updated = { ...item, [field]: value };

        // Auto-calculate price when unit_price or count changes
        if (field === 'unit_price' || field === 'count') {
          updated.price = updated.unit_price * updated.count;
        }

        return updated;
      })
    );
  };

  const handleAddItem = () => {
    const newId = Math.max(0, ...items.map((i) => i.id)) + 1;
    setItems([
      ...items,
      { id: newId, name: '', unit_price: 0, count: 1, price: 0 },
    ]);
  };

  const handleDeleteItem = (id: number) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const totalPrice = items.reduce((sum, item) => sum + item.price, 0);

  return (
    <div className="max-w-6xl mx-auto animate-fadeIn">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">
          <span className="text-gradient">영수증 정보</span>
        </h2>
        <p className="text-gray-600 dark:text-gray-400">추출된 데이터를 확인하고 필요시 수정하세요</p>
      </div>

      {/* Basic Info */}
      <div className="card-hover p-6 mb-6">
        <h3 className="font-semibold text-lg mb-4 text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <PenLine className="w-5 h-5 text-primary-500" /> 기본 정보
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-2">영수증 ID</label>
            <input
              type="text"
              value={data.receipt_id}
              disabled
              className="input-field bg-gray-50 dark:bg-slate-600 cursor-not-allowed"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-2">가게명</label>
            <input
              type="text"
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              className="input-field"
            />
          </div>
        </div>
      </div>

      {/* Items Table */}
      <div className="card-hover p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-primary-500" /> 구매 품목
          </h3>
          <button
            onClick={handleAddItem}
            className="btn-primary text-sm inline-flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" /> 품목 추가
          </button>
        </div>

        <div className="overflow-x-auto -mx-6 px-6">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b-2 border-gray-200 dark:border-slate-600">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider w-16">ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">품목명</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider w-32">단가</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider w-24">수량</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider w-32">금액</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider w-24">삭제</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-slate-600">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors">
                  <td className="px-4 py-3 text-center text-sm text-gray-600 dark:text-gray-400">{item.id}</td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(e) => handleItemChange(item.id, 'name', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 dark:bg-slate-700 dark:text-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                      placeholder="품목명 입력"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      value={item.unit_price}
                      onChange={(e) => handleItemChange(item.id, 'unit_price', Number(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 dark:bg-slate-700 dark:text-gray-200 rounded-lg text-right focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      value={item.count}
                      onChange={(e) => handleItemChange(item.id, 'count', Number(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 dark:bg-slate-700 dark:text-gray-200 rounded-lg text-center focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                      min="1"
                    />
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-gray-100">
                    {'\u20A9'}{item.price.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 p-2 rounded-lg transition-all hover:scale-110"
                      title="삭제"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t-2 border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50">
              <tr>
                <td colSpan={4} className="px-4 py-4 text-right font-semibold text-gray-700 dark:text-gray-300">
                  총합계
                </td>
                <td className="px-4 py-4 text-right text-lg font-bold text-gradient">
                  {'\u20A9'}{totalPrice.toLocaleString()}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="mt-6 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
          <div className="flex items-start gap-2">
            <Lightbulb className="w-5 h-5 text-primary-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-primary-900 dark:text-primary-300 mb-2">편집 방법</p>
              <ul className="text-sm text-primary-800 dark:text-primary-300/80 space-y-1">
                <li>• 단가와 수량을 수정하면 금액이 자동으로 계산됩니다</li>
                <li>• 품목 추가 버튼으로 새 행을 추가할 수 있습니다</li>
                <li>• 휴지통 아이콘으로 품목을 삭제할 수 있습니다</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
