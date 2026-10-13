import type { JointOptions } from "../jointTypes.ts"

// Testdata för alternativen ur underlaget. Formen följer kontraktet GET /api/joint-runs/options; värdena är påhittade.
// Appkod får aldrig importera den här filen. Riktiga svar finns som ögonblicksbild i testing/contract/options.json.

export const OPTIONS: JointOptions = {
  scenario_id: "joint_real_subset", data_available: true, plan_area: "Uppsala",
  rooms: [
    { room_id: "A-101", label: "Storgatan 1 – A-101 (120 platser)", building_id: "A", address: "Storgatan 1", capacity: 120, digital: "all" },
    { room_id: "A-102", label: "Storgatan 1 – A-102 (60 platser)", building_id: "A", address: "Storgatan 1", capacity: 60, digital: "partial" },
    { room_id: "B-201", label: "B-201", building_id: "B", address: "Lillgatan 2", capacity: 30, digital: "none" },
    { room_id: "B-202", label: "Lillgatan 2 – B-202", building_id: "B", address: "Lillgatan 2", capacity: null, digital: "unknown" },
    { room_id: "X-1", label: "X-1", building_id: null, address: null, capacity: 10, digital: "unknown" },
  ],
  exam_types: [
    { value: "ordinarie tentamen", label: "Ordinarie tentamen", count: 120 },
    { value: "omtenta", label: "Omtenta", count: 40 },
    { value: "dugga", label: "Dugga", count: 22 },
    { value: "hybridtenta", label: "Hybridtenta", count: 5 },
    { value: "hemtenta", label: "Hemtenta", count: 9 },
  ],
}

export const NO_OPTIONS: JointOptions = { scenario_id: "joint_real_subset", data_available: false, plan_area: null, rooms: [], exam_types: [] }
