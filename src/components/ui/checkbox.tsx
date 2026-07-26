"use client";

import * as React from "react";

export function Checkbox({
  checked,
  onCheckedChange,
  label,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label?: string;
}) {
  return (
    <label className="flex items-center space-x-2 cursor-pointer select-none">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onCheckedChange(e.target.checked)}
        className="h-4 w-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-400"
      />
      {label && <span className="text-gray-700">{label}</span>}
    </label>
  );
}
