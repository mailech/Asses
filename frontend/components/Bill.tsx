import type { Booking } from "@/lib/types";
import { billDate, mealPlanLabel, money, plural, roomLabel } from "@/lib/format";

interface Props {
  booking: Booking;
}

/**
 * The bill. This is the artefact the production office prints and emails, so it
 * is laid out as a document -- issuer, reference, parties, line items, totals --
 * rather than as a set of cards.
 *
 * The request it was raised from is shown in full, always. A bill that has lost
 * the words it came from cannot be checked against the email that asked for it.
 */
export function Bill({ booking }: Props) {
  const { request, quote } = booking;
  const currency = quote.currency;
  const roomCount = request.rooms.reduce((sum, room) => sum + room.quantity, 0);

  return (
    <article className="panel bill" aria-label={`Bill ${booking.reference}`}>
      <header className="bill__head">
        <div>
          <div className="bill__issuer">Production office</div>
          <p className="bill__issuer-line">Crew accommodation</p>
          <p className="bill__issuer-line">Standing rate card, {currency}</p>
        </div>
        <div className="bill__meta">
          <div className="bill__kind">Accommodation bill</div>
          <p className="bill__reference">{booking.reference}</p>
          <p className="bill__issued">Issued {billDate(booking.created_at)}</p>
          <span className="bill__stamp">Confirmed</span>
        </div>
      </header>

      <div className="bill__parties">
        <div>
          <div className="bill__party-label">Booked for</div>
          <p className="bill__party-value">
            {request.party ?? "The production"}
            <span className="bill__party-note">
              {plural(quote.guests, "guest")}
              {request.guest_count_source === "derived_from_capacity"
                ? " · assumed full occupancy"
                : " · as requested"}
            </span>
          </p>
        </div>
        <div>
          <div className="bill__party-label">Stay</div>
          <p className="bill__party-value">
            {plural(quote.nights, "night")}
            <span className="bill__party-note">
              {mealPlanLabel(quote.meal_plan)}
            </span>
          </p>
        </div>
        <div>
          <div className="bill__party-label">Rooms</div>
          <p className="bill__party-value">
            {request.rooms
              .map(
                (room) =>
                  `${room.quantity} ${roomLabel(room.room_type, room.quantity)}`,
              )
              .join(", ")}
            <span className="bill__party-note">{plural(roomCount, "room")} in total</span>
          </p>
        </div>
      </div>

      <section className="bill__prompt">
        <div className="bill__party-label">Request as received</div>
        <p className="bill__prompt-text">“{booking.raw_input}”</p>
      </section>

      <div className="breakdown-scroll">
        <table className="breakdown">
          <caption>Cost breakdown</caption>
          <thead>
            <tr>
              <th scope="col">Room</th>
              <th scope="col" className="numeric">
                Rooms
              </th>
              <th scope="col" className="numeric">
                Lodging
              </th>
              <th scope="col" className="numeric">
                Meals
              </th>
              <th scope="col" className="numeric">
                Line total
              </th>
            </tr>
          </thead>
          <tbody>
            {quote.rooms.map((line) => (
              <tr key={line.room_type}>
                <th scope="row" className="breakdown__room">
                  {roomLabel(line.room_type)}
                  <span className="breakdown__detail">
                    {money(line.nightly_rate, currency)} per night · sleeps{" "}
                    {line.capacity_per_room}
                  </span>
                </th>
                <td className="numeric figure">{line.quantity}</td>
                <td className="numeric figure">{money(line.room_charge, currency)}</td>
                <td className="numeric figure">
                  {money(line.meal_charge, currency)}
                  {Number(line.meal_rate_per_guest_night) > 0 ? (
                    <span className="breakdown__detail">
                      {line.guests_allocated > 0
                        ? `${plural(line.guests_allocated, "guest")} × ${money(
                            line.meal_rate_per_guest_night,
                            currency,
                          )} × ${plural(line.nights, "night")}`
                        : "no guests seated"}
                    </span>
                  ) : null}
                </td>
                <td className="numeric figure">{money(line.subtotal, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="totals">
        <div className="totals__row">
          <span>Lodging</span>
          <span className="figure">{money(quote.room_subtotal, currency)}</span>
        </div>
        <div className="totals__row">
          <span>Meals</span>
          <span className="figure">{money(quote.meal_subtotal, currency)}</span>
        </div>
        <div className="totals__row">
          <span>Subtotal</span>
          <span className="figure">{money(quote.subtotal, currency)}</span>
        </div>
        {quote.discount.applied ? (
          <div className="totals__row totals__row--discount">
            <span>
              Extended stay · {quote.discount.percent}% over{" "}
              {quote.discount.threshold_nights} nights
            </span>
            <span className="figure">−{money(quote.discount.amount, currency)}</span>
          </div>
        ) : null}
        <div className="totals__row totals__row--grand">
          <span>Total due</span>
          <span className="figure">{money(quote.total, currency)}</span>
        </div>
      </div>

      {request.warnings.length > 0 ? (
        <section className="footnotes">
          <h3 className="eyebrow">Assumptions made</h3>
          <ul className="footnotes__list">
            {request.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className="bill__foot">
        Priced against the standing rate card at the time of booking. This bill is
        a record of that price and does not change if the rate card does.
        Reference {booking.reference} · booking {booking.booking_id}.
      </footer>
    </article>
  );
}
