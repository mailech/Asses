import type { MealPlan, RoomType } from "./types";

/**
 * Turn the builder's selections into the sentence a person would have typed.
 *
 * The builder does not get its own endpoint. It writes English and posts it
 * like any other request, so there is one ingestion path, one set of rules, and
 * every bill — however it was raised — still shows the words it came from.
 *
 * `backend/tests/test_parser.py::TestComposedRequests` pins these exact shapes.
 */

const ROOM_PHRASES: Record<RoomType, [singular: string, plural: string]> = {
  single: ["single room", "single rooms"],
  double: ["double room", "double rooms"],
  suite: ["suite", "suites"],
  dormitory: ["dormitory", "dormitories"],
  apartment: ["apartment", "apartments"],
  guesthouse: ["guesthouse", "guesthouses"],
};

const MEAL_PHRASES: Record<MealPlan, string> = {
  none: "room only",
  breakfast: "with breakfast",
  half_board: "with half board",
  full_board: "with full board",
};

export interface RoomChoice {
  roomType: RoomType;
  quantity: number;
}

export interface BuilderSelection {
  rooms: RoomChoice[];
  nights: number;
  mealPlan: MealPlan;
  guests: number | null;
  party: string;
}

function joinWithAnd(parts: string[]): string {
  if (parts.length <= 1) return parts[0] ?? "";
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

export function roomPhrase({ roomType, quantity }: RoomChoice): string {
  const [singular, plural] = ROOM_PHRASES[roomType];
  return `${quantity} ${quantity === 1 ? singular : plural}`;
}

export function composeRequest(selection: BuilderSelection): string {
  const { rooms, nights, mealPlan, guests, party } = selection;

  const clauses = [
    `Book ${joinWithAnd(rooms.map(roomPhrase))}`,
    `for ${nights} ${nights === 1 ? "night" : "nights"}`,
    MEAL_PHRASES[mealPlan],
  ];

  if (guests !== null) {
    clauses.push(`for ${guests} ${guests === 1 ? "person" : "people"}`);
  }

  const who = party.trim();
  if (who) clauses.push(`for ${who}`);

  return clauses.join(" ");
}
