"use client";

import { useMemo, useState } from "react";

import { composeRequest, type RoomChoice } from "@/lib/compose";
import { mealPlanLabel } from "@/lib/format";
import type { MealPlan, RoomType } from "@/lib/types";

/** Mirrors the rate card in `backend/app/domain/catalog.py`. */
const ROOM_OPTIONS: Array<{ value: RoomType; label: string; sleeps: number }> = [
  { value: "single", label: "Single", sleeps: 1 },
  { value: "double", label: "Double", sleeps: 2 },
  { value: "suite", label: "Suite", sleeps: 2 },
  { value: "dormitory", label: "Dormitory", sleeps: 8 },
  { value: "apartment", label: "Apartment", sleeps: 4 },
  { value: "guesthouse", label: "Guesthouse", sleeps: 3 },
];

const MEAL_OPTIONS: MealPlan[] = ["none", "breakfast", "half_board", "full_board"];

const QUANTITIES = Array.from({ length: 20 }, (_, index) => index + 1);

interface Props {
  pending: boolean;
  onSubmit: (text: string) => void;
}

export function RequestBuilder({ pending, onSubmit }: Props) {
  const [rooms, setRooms] = useState<RoomChoice[]>([
    { roomType: "double", quantity: 1 },
  ]);
  // Held as text so clearing the field shows an empty box, not a 0.
  const [nights, setNights] = useState("7");
  const [mealPlan, setMealPlan] = useState<MealPlan>("none");
  const [guests, setGuests] = useState("");
  const [party, setParty] = useState("");

  const capacity = rooms.reduce((total, room) => {
    const option = ROOM_OPTIONS.find((candidate) => candidate.value === room.roomType);
    return total + (option ? option.sleeps * room.quantity : 0);
  }, 0);

  const nightsValue = Number(nights);
  const nightsValid =
    nights.trim() !== "" &&
    Number.isInteger(nightsValue) &&
    nightsValue >= 1 &&
    nightsValue <= 365;

  const request = useMemo(
    () =>
      composeRequest({
        rooms,
        nights: nightsValid ? nightsValue : 1,
        mealPlan,
        guests: guests.trim() === "" ? null : Number(guests),
        party,
      }),
    [rooms, nightsValid, nightsValue, mealPlan, guests, party],
  );

  const unusedRoomTypes = ROOM_OPTIONS.filter(
    (option) => !rooms.some((room) => room.roomType === option.value),
  );

  const updateRoom = (index: number, change: Partial<RoomChoice>) =>
    setRooms((current) =>
      current.map((room, position) =>
        position === index ? { ...room, ...change } : room,
      ),
    );

  const guestsValid =
    guests.trim() === "" || (Number(guests) >= 1 && Number(guests) <= capacity);
  const canSubmit = rooms.length > 0 && nightsValid && guestsValid && !pending;

  return (
    <section className="panel builder no-print" aria-labelledby="builder-heading">
      <h2 className="eyebrow" id="builder-heading">
        Or build it from the rate card
      </h2>
      <p className="builder__intro">
        Choose the rooms and the service writes the request for you, so the bill
        still records the words it was raised from.
      </p>

      <div className="builder__rooms">
        {rooms.map((room, index) => (
          <div className="builder__room" key={room.roomType}>
            <label className="visually-hidden" htmlFor={`room-type-${index}`}>
              Room type
            </label>
            <select
              id={`room-type-${index}`}
              className="control"
              value={room.roomType}
              onChange={(event) =>
                updateRoom(index, { roomType: event.target.value as RoomType })
              }
            >
              {ROOM_OPTIONS.filter(
                (option) =>
                  option.value === room.roomType ||
                  unusedRoomTypes.includes(option),
              ).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} · sleeps {option.sleeps}
                </option>
              ))}
            </select>

            <label className="visually-hidden" htmlFor={`room-quantity-${index}`}>
              How many {room.roomType} rooms
            </label>
            <select
              id={`room-quantity-${index}`}
              className="control"
              value={room.quantity}
              onChange={(event) =>
                updateRoom(index, { quantity: Number(event.target.value) })
              }
            >
              {QUANTITIES.map((quantity) => (
                <option key={quantity} value={quantity}>
                  × {quantity}
                </option>
              ))}
            </select>

            <button
              type="button"
              className="builder__remove"
              aria-label={`Remove ${room.roomType}`}
              disabled={rooms.length === 1}
              onClick={() =>
                setRooms((current) =>
                  current.filter((_, position) => position !== index),
                )
              }
            >
              −
            </button>
          </div>
        ))}
      </div>

      <button
        type="button"
        className="builder__add"
        disabled={unusedRoomTypes.length === 0}
        onClick={() => {
          const next = unusedRoomTypes[0];
          if (next) setRooms((current) => [...current, { roomType: next.value, quantity: 1 }]);
        }}
      >
        + Add another room type
      </button>

      <div className="builder__grid">
        <div className="field">
          <label className="field__label" htmlFor="builder-nights">
            Nights
          </label>
          <input
            id="builder-nights"
            className="control"
            type="number"
            min={1}
            max={365}
            value={nights}
            onChange={(event) => setNights(event.target.value)}
          />
        </div>

        <div className="field">
          <label className="field__label" htmlFor="builder-meals">
            Meal plan
          </label>
          <select
            id="builder-meals"
            className="control"
            value={mealPlan}
            onChange={(event) => setMealPlan(event.target.value as MealPlan)}
          >
            {MEAL_OPTIONS.map((plan) => (
              <option key={plan} value={plan}>
                {mealPlanLabel(plan)}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="field__label" htmlFor="builder-guests">
            Guests
          </label>
          <input
            id="builder-guests"
            className="control"
            type="number"
            min={1}
            max={capacity}
            placeholder={`All ${capacity}`}
            value={guests}
            onChange={(event) => setGuests(event.target.value)}
          />
        </div>

        <div className="field">
          <label className="field__label" htmlFor="builder-party">
            For
          </label>
          <input
            id="builder-party"
            className="control"
            type="text"
            maxLength={80}
            placeholder="the lead cast"
            value={party}
            onChange={(event) => setParty(event.target.value)}
          />
        </div>
      </div>

      <p className="builder__summary">
        {nightsValid ? (
          <>
            Will be sent as: <em>“{request}”</em>
          </>
        ) : (
          "Enter a stay between 1 and 365 nights."
        )}
      </p>

      {!guestsValid ? (
        <div className="notice" role="alert">
          <p className="notice__message">
            These rooms sleep {capacity}. Reduce the guest count, or add rooms.
          </p>
        </div>
      ) : null}

      <div className="builder__actions">
        <button
          type="button"
          className="button"
          disabled={!canSubmit}
          onClick={() => onSubmit(request)}
        >
          {pending ? "Costing…" : "Generate bill"}
        </button>
      </div>
    </section>
  );
}
