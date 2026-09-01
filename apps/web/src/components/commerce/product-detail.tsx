"use client";

import {
  useEffect,
  useRef,
} from "react";

import {
  ShoppingBag,
  X,
} from "lucide-react";

import type {
  Product,
  TelemetryEvent,
} from "@/types/commerce";

import type {
  TrackEventOptions,
} from "@/hooks/use-telemetry";


type EventInput = Omit<
  TelemetryEvent,
  "session_id"
>;


type ProductDetailProps = {
  product: Product;

  onClose: () => void;

  onAddToCart: (
    product: Product
  ) => void;

  trackEvent: (
    event: EventInput,
    options?: TrackEventOptions
  ) => Promise<void>;
};


const SCROLL_THRESHOLDS = [
  0.25,
  0.5,
  0.75,
  1,
];


export function ProductDetail({
  product,
  onClose,
  onAddToCart,
  trackEvent,
}: ProductDetailProps) {
  const seenThresholds =
    useRef(
      new Set<number>()
    );


  useEffect(() => {
    const openedAt =
      performance.now();

    const previousOverflow =
      document.body.style.overflow;

    document.body.style.overflow =
      "hidden";


    void trackEvent(
      {
        event_type:
          "view_item",

        product_id:
          product.product_id,

        category_id:
          product.category_id,

        metadata: {
          surface:
            "product_detail",

          brand:
            product.brand,

          category:
            product.category_code,
        },
      },
      {
        refreshRecommendations:
          false,
      }
    );


    function handleKeyDown(
      event: KeyboardEvent
    ) {
      if (
        event.key ===
        "Escape"
      ) {
        onClose();
      }
    }


    window.addEventListener(
      "keydown",
      handleKeyDown
    );


    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );

      document.body.style.overflow =
        previousOverflow;

      const dwellTimeMs =
        Math.round(
          performance.now()
          - openedAt
        );

      if (
        dwellTimeMs >=
        1000
      ) {
        void trackEvent({
          event_type:
            "dwell_time",

          product_id:
            product.product_id,

          category_id:
            product.category_id,

          metadata: {
            dwell_time_ms:
              dwellTimeMs,

            surface:
              "product_detail",
          },
        });
      }
    };
  }, [
    onClose,
    product,
    trackEvent,
  ]);


  function handleScroll(
    event:
      React.UIEvent<HTMLDivElement>
  ) {
    const element =
      event.currentTarget;

    const availableScroll =
      element.scrollHeight
      - element.clientHeight;

    if (
      availableScroll <= 0
    ) {
      return;
    }

    const actualDepth =
      element.scrollTop
      / availableScroll;


    for (
      const threshold
      of SCROLL_THRESHOLDS
    ) {
      if (
        actualDepth >=
          threshold
        &&
        !seenThresholds
          .current
          .has(
            threshold
          )
      ) {
        seenThresholds
          .current
          .add(
            threshold
          );

        void trackEvent(
          {
            event_type:
              "scroll_depth",

            product_id:
              product.product_id,

            category_id:
              product.category_id,

            metadata: {
              depth:
                threshold,

              actual_depth:
                Number(
                  actualDepth
                    .toFixed(
                      4
                    )
                ),

              surface:
                "product_detail",
            },
          },
          {
            refreshRecommendations:
              false,
          }
        );
      }
    }
  }


  return (
    <div
      className="product-detail-backdrop"
      onMouseDown={(
        event
      ) => {
        if (
          event.target ===
          event.currentTarget
        ) {
          onClose();
        }
      }}
    >
      <aside
        className="product-detail"
        role="dialog"
        aria-modal="true"
        aria-label={
          product.name
        }
      >
        <div className="product-detail-header">
          <span>
            PRODUCT /
            {product.product_id}
          </span>

          <button
            type="button"
            onClick={
              onClose
            }
            aria-label="Close product details"
          >
            <X
              size={20}
              strokeWidth={
                1.5
              }
            />
          </button>
        </div>


        <div
          className="product-detail-scroll"
          onScroll={
            handleScroll
          }
        >
          <div className="product-detail-visual">
            <span>
              {(
                product.brand
                ??
                product.category_leaf
                ??
                "PR"
              )
                .slice(
                  0,
                  2
                )
                .toUpperCase()}
            </span>
          </div>


          <div className="product-detail-copy">
            <div className="product-detail-meta">
              <span>
                {product.brand ??
                  "Independent"}
              </span>

              <span>
                {product.category_code ??
                  "collection"}
              </span>
            </div>


            <h2>
              {product.name}
            </h2>


            <strong className="product-detail-price">
              $
              {product.price
                .toLocaleString(
                  "en-US",
                  {
                    minimumFractionDigits:
                      2,

                    maximumFractionDigits:
                      2,
                  }
                )}
            </strong>


            <p>
              This product is part
              of the behavioral
              commerce catalog used
              by the personalization
              engine.
            </p>


            <div className="product-detail-data">
              <div>
                <span>
                  PURCHASES
                </span>

                <strong>
                  {product.purchases
                    .toLocaleString()}
                </strong>
              </div>

              <div>
                <span>
                  VIEWS
                </span>

                <strong>
                  {product.views
                    .toLocaleString()}
                </strong>
              </div>

              <div>
                <span>
                  CONVERSION
                </span>

                <strong>
                  {(
                    product
                      .view_to_purchase_rate
                    * 100
                  ).toFixed(
                    2
                  )}
                  %
                </strong>
              </div>

              <div>
                <span>
                  INVENTORY
                </span>

                <strong>
                  {
                    product
                      .inventory_quantity
                  }
                </strong>
              </div>
            </div>


            <div className="product-detail-story">
              <span>
                BEHAVIORAL SIGNAL
              </span>

              <h3>
                Your interaction
                with this product
                changes the live
                recommendation
                model.
              </h3>

              <p>
                Product views,
                engagement depth,
                dwell time and cart
                intent are converted
                into weighted session
                signals and projected
                into the learned
                latent product space.
              </p>
            </div>


            <div className="product-detail-story">
              <span>
                REAL-TIME
                PERSONALIZATION
              </span>

              <h3>
                Intent evolves
                during the session.
              </h3>

              <p>
                Stronger and more
                recent interactions
                receive more influence
                while older behavior
                gradually decays.
                Recommendations are
                re-ranked without
                retraining the model.
              </p>
            </div>
          </div>
        </div>


        <div className="product-detail-footer">
          <div>
            <span>
              {
                product
                  .inventory_quantity
              }{" "}
              AVAILABLE
            </span>

            <strong>
              $
              {product.price
                .toFixed(
                  2
                )}
            </strong>
          </div>

          <button
            type="button"
            onClick={() =>
              onAddToCart(
                product
              )
            }
          >
            <ShoppingBag
              size={17}
              strokeWidth={
                1.5
              }
            />

            ADD TO BAG
          </button>
        </div>
      </aside>
    </div>
  );
}