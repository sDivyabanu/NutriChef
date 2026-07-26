"use client";

import { useEffect, useState } from "react";
import { Pencil, Check, X } from "lucide-react";

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [tempValue, setTempValue] = useState<string>("");

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await fetch("/api/profile");
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.message);
        setProfile(data);
      } catch (err) {
        console.error("Error fetching profile:", err);
        alert("Failed to load profile. Please log in again.");
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const startEditing = (field: string, value: any) => {
    setEditingField(field);
    setTempValue(value ? String(value) : "");
  };

  const cancelEditing = () => {
    setEditingField(null);
    setTempValue("");
  };

  const saveField = async (field: string) => {
    try {
      const updated = { ...profile, [field]: tempValue };
      setProfile(updated);
      setEditingField(null);

      // Update backend
      const res = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: tempValue }),
      });

      if (!res.ok) throw new Error("Failed to update field");
    } catch (err) {
      console.error("Failed to update:", err);
      alert("Error updating profile.");
    }
  };

  if (loading) return <p className="text-center mt-10">Loading...</p>;
  if (!profile) return <p className="text-center mt-10">No profile found.</p>;

  const renderField = (label: string, field: string, value: any) => (
    <div key={field} className="flex items-center justify-between border-b py-2">
      <div className="flex-1">
        <label htmlFor={field} className="font-semibold text-gray-800">
          {label}
        </label>
        {editingField === field ? (
          <input
            id={field}
            className="mt-1 w-full border rounded-lg px-2 py-1 text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            placeholder={`Enter ${label.toLowerCase()}`}
            value={tempValue}
            onChange={(e) => setTempValue(e.target.value)}
          />
        ) : (
          <p className="text-gray-600 mt-1 break-words">
            {Array.isArray(value)
              ? value.length > 0
                ? value.join(", ")
                : "None"
              : value || "None"}
          </p>
        )}
      </div>

      {editingField === field ? (
        <div className="flex space-x-2 ml-3">
          <button
            type="button"
            title={`Save ${label}`}
            onClick={() => saveField(field)}
            className="text-emerald-600 hover:text-emerald-800"
          >
            <Check size={18} aria-hidden="true" />
            <span className="sr-only">Save</span>
          </button>
          <button
            type="button"
            title={`Cancel editing ${label}`}
            onClick={cancelEditing}
            className="text-gray-500 hover:text-gray-700"
          >
            <X size={18} aria-hidden="true" />
            <span className="sr-only">Cancel</span>
          </button>
        </div>
      ) : (
        <button
          type="button"
          title={`Edit ${label}`}
          onClick={() => startEditing(field, value)}
          className="text-gray-500 hover:text-emerald-600 ml-3"
        >
          <Pencil size={18} aria-hidden="true" />
          <span className="sr-only">Edit</span>
        </button>
      )}
    </div>
  );

  return (
    <div className="max-w-md mx-auto mt-10 bg-white shadow-lg p-6 rounded-2xl">
      <h2 className="text-2xl font-bold mb-4 text-emerald-600 text-center">
        Your Profile 🌿
      </h2>

      <div className="space-y-3 text-gray-700">
        {renderField("Height (cm)", "height_cm", profile.height_cm)}
        {renderField("Weight (kg)", "weight_kg", profile.weight_kg)}
        {renderField("Age", "age", profile.age)}
        {renderField("Diet Type", "diet_type", profile.diet_type)}
        {renderField("Allergies", "allergies", profile.allergies)}
        {renderField("Conditions", "health_conditions", profile.health_conditions)}
        {renderField("Other Info", "other_info", profile.other_info)}
      </div>
    </div>
  );
}
