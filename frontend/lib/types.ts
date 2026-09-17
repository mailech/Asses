/**
 * The API's response shapes.
 *
 * Money arrives as a string ("7565.00") rather than a number: the service keeps
 * its arithmetic in decimals, and parsing it into a float here would be the one
 * place a cent could go missing. Strings are formatted for display, never
 * summed — the totals are the service's job.
 */

export type MealPlan = "none" | "breakfast" | "half_board" | "full_board";

export type RoomType =
  | "single"
  | "double"
  | "suite"
  | "dormitory"
  | "apartment"
  | "guesthouse";

export interface RoomSelection {
  room_type: RoomType;
  quantity: number;
}

export interface ParsedRequest {
  rooms: RoomSelection[];
  nights: number;
  meal_plan: MealPlan;
  guests: number;
  guest_count_source: "stated" | "derived_from_capacity";
  party: string | null;
  warnings: string[];
}

export interface RoomLine {
  room_type: RoomType;
  category: "budget" | "standard" | "premium";
  quantity: number;
  capacity_per_room: number;
  nightly_rate: string;
  nights: number;
  room_charge: string;
  guests_allocated: number;
  meal_rate_per_guest_night: string;
  meal_charge: string;
  subtotal: string;
}

export interface Discount {
  applied: boolean;
  reason: string;
  threshold_nights: number;
  percent: string;
  amount: string;
}

export interface Quote {
  currency: string;
  nights: number;
  guests: number;
  meal_plan: MealPlan;
  rooms: RoomLine[];
  room_subtotal: string;
  meal_subtotal: string;
  subtotal: string;
  discount: Discount;
  total: string;
}

export interface Booking {
  booking_id: string;
  reference: string;
  created_at: string;
  raw_input: string;
  request: ParsedRequest;
  quote: Quote;
}

export interface BookingSummary {
  booking_id: string;
  reference: string;
  created_at: string;
  raw_input: string;
  nights: number;
  guests: number;
  room_count: number;
  meal_plan: MealPlan;
  currency: string;
  total: string;
}

export interface BookingPage {
  items: BookingSummary[];
  count: number;
  limit: number;
  offset: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; hint: string | null };
}
