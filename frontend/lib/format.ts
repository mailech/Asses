import type { MealPlan, RoomType } from "./types";

const MEAL_PLAN_LABELS: Record<MealPlan, string> = {
  none: "Room only",
  breakfast: "Breakfast",
  half_board: "Half board",
  full_board: "Full board",
};

/** Singular and plural spelled out: "Dormitory" does not pluralise with an s. */
const ROOM_LABELS: Record<RoomType, [singular: string, plural: string]> = {
  single: ["Single", "Singles"],
  double: ["Double", "Doubles"],
  suite: ["Suite", "Suites"],
  dormitory: ["Dormitory", "Dormitories"],
  apartment: ["Apartment", "Apartments"],
  guesthouse: ["Guesthouse", "Guesthouses"],
};

export function mealPlanLabel(plan: MealPlan): string {
  return MEAL_PLAN_LABELS[plan];
}

export function roomLabel(room: RoomType, quantity = 1): string {
  const [singular, plural] = ROOM_LABELS[room];
  return quantity === 1 ? singular : plural;
}

/** Format an amount the API sent as a decimal string, e.g. "7565.00". */
export function money(amount: string, currency: string): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) return amount;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(value);
}

export function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

export function timestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** The date as it reads on a bill: "17 September 2026". */
export function billDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
