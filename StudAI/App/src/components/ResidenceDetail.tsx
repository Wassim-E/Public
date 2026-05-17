import "./ResidenceDetail.css";
import { useState } from "react";
import type { Housing, PriceSource, ReviewEntry, CommuteResult } from "../types";

type Props = {
  housing: Housing;
  onClose: () => void;
  commuteResult?: CommuteResult | null;
};

export function ResidenceDetail({ housing: h, onClose, commuteResult }: Props) {
  const [reviewsOpen, setReviewsOpen] = useState(false);

  return (
    <div className="detail-panel">
      <div className="detail-header">
        <div className="detail-header-text">
          <div className="detail-name">{h.name}</div>
          {h.provider && <div className="detail-provider">{h.provider}</div>}
        </div>
        <button className="detail-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      {/* Image */}
      {h.imageUrl && (
        <div className="detail-image-wrap">
          <img className="detail-image" src={h.imageUrl} alt={h.name} />
        </div>
      )}

      {/* Quick facts */}
      <div className="detail-facts">
        {h.address && <div className="detail-fact"><span className="fact-label">Address</span>{h.address}</div>}
        {h.type && <div className="detail-fact"><span className="fact-label">Type</span>{h.type}</div>}
        {h.distance && <div className="detail-fact"><span className="fact-label">Distance</span>{h.distance}</div>}
        {commuteResult && (
          <div className="detail-fact">
            <span className="fact-label">Commute</span>
            <span className="detail-commute-inline">
              ~{commuteResult.minutes} min
              <span className="detail-commute-tag">transit est.</span>
            </span>
          </div>
        )}
        {h.phone && (
          <div className="detail-fact">
            <span className="fact-label">Phone</span>
            <a href={`tel:${h.phone}`} className="detail-link">{h.phone}</a>
          </div>
        )}
        {h.googleRating && (
          <div className="detail-fact">
            <span className="fact-label">Google</span>
            <a href={h.googleMapsUrl} target="_blank" rel="noreferrer" className="detail-link detail-rating">
              ★ {h.googleRating.toFixed(1)}
              {h.googleRatingCount != null && (
                <span className="detail-rating-count"> · {h.googleRatingCount} avis</span>
              )}
            </a>
          </div>
        )}
      </div>

      {/* Description */}
      {h.description && (
        <div className="detail-section">
          <div className="detail-section-title">Description</div>
          <p className="detail-description">{h.description}</p>
        </div>
      )}

      {/* Price sources */}
      {h.prices && h.prices.length > 0 && (
        <div className="detail-section">
          <div className="detail-section-title">Prices by source</div>
          <div className="detail-prices">
            {h.prices.map((p) => (
              <PriceCard key={p.source} price={p} />
            ))}
          </div>
        </div>
      )}

      {/* Amenities */}
      {h.amenities && h.amenities.length > 0 && (
        <div className="detail-section">
          <div className="detail-section-title">Amenities</div>
          <div className="detail-amenities">
            {h.amenities.map((a) => (
              <span key={a} className="detail-amenity-tag">{a}</span>
            ))}
          </div>
        </div>
      )}

      {/* Google Reviews — collapsible */}
      {h.googleReviews && h.googleReviews.length > 0 && (
        <div className="detail-section detail-section--reviews">
          <button
            className="detail-reviews-toggle"
            onClick={() => setReviewsOpen((v) => !v)}
            aria-expanded={reviewsOpen}
          >
            <span className="detail-section-title" style={{ margin: 0 }}>
              Google Reviews
              {h.googleRatingCount != null && (
                <span className="detail-section-sub"> · {h.googleRatingCount} total</span>
              )}
            </span>
            <svg
              className={`detail-chevron${reviewsOpen ? " is-open" : ""}`}
              width="12"
              height="12"
              viewBox="0 0 12 12"
            >
              <path
                d="M2 4L6 8L10 4"
                stroke="currentColor"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          {reviewsOpen && (
            <div className="detail-reviews">
              {h.googleReviews.map((r, i) => (
                <ReviewCard key={i} review={r} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PriceCard({ price: p }: { price: PriceSource }) {
  const rentStr = p.rent
    ? p.rentMax && p.rentMax !== p.rent
      ? `${p.rent} – ${p.rentMax} €/mo`
      : `${p.rent} €/mo`
    : null;
  const surfStr = p.surface
    ? p.surfaceMax && p.surfaceMax !== p.surface
      ? `${p.surface} – ${p.surfaceMax} m²`
      : `${p.surface} m²`
    : null;

  return (
    <div className="price-card">
      <div className="price-card-header">
        <span className="price-card-label">{p.sourceLabel}</span>
        {p.url && (
          <a href={p.url} target="_blank" rel="noreferrer" className="price-card-link">
            View ↗
          </a>
        )}
      </div>
      {(rentStr || surfStr) && (
        <div className="price-card-values">
          {rentStr && <span className="price-card-rent">{rentStr}</span>}
          {surfStr && <span className="price-card-surface">{surfStr}</span>}
        </div>
      )}
      {p.rooms && p.rooms.length > 0 && (
        <div className="price-rooms">
          {p.rooms.map((r, i) => (
            <div key={i} className="price-room-row">
              <span className="price-room-type">{r.type ?? "—"}</span>
              {r.rent && <span className="price-room-rent">{r.rent} €</span>}
              {r.surface && <span className="price-room-surface">{r.surface} m²</span>}
              {r.available != null && (
                <span className={`price-room-avail ${r.available ? "avail--yes" : "avail--no"}`}>
                  {r.available ? "Available" : "Occupied"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const REVIEW_MAX = 200;

function ReviewCard({ review: r }: { review: ReviewEntry }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = r.text && r.text.length > REVIEW_MAX;

  return (
    <div className="review-card">
      <div className="review-header">
        <span className="review-author">{r.author || "Anonymous"}</span>
        {r.rating != null && (
          <span className="review-stars">{"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}</span>
        )}
        <span className="review-date">{r.date}</span>
      </div>
      {r.text && (
        <p className="review-text">
          {isLong && !expanded ? r.text.slice(0, REVIEW_MAX) + "…" : r.text}
        </p>
      )}
      {isLong && (
        <button className="review-more" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Show less" : "More"}
        </button>
      )}
    </div>
  );
}
