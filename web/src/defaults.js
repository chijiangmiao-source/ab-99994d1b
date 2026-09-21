// Default scenario: unequal masses, some restrictions, one tube whose current
// slot is outside its allowed set. Gives the audit console something real to
// show on first load.
export const SLOT_COUNT = 8

export const defaultTubes = [
  { label: 'A', mass: 12, current_slot: 0, allowed_slots: [0, 1, 4, 5] },
  { label: 'B', mass: 8, current_slot: 3, allowed_slots: [2, 3, 4, 6, 7] },
  { label: 'C', mass: 8, current_slot: 5, allowed_slots: [1, 2, 5, 6] },
  { label: 'D', mass: 5, current_slot: 2, allowed_slots: [0, 4] },
]
