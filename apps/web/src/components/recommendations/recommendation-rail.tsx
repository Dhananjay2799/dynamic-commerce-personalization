"use client";

import {
  ArrowRight,
  Radio,
} from "lucide-react";

import {
  ProductCard,
} from "@/components/commerce/product-card";

import {
  ImpressionTracker,
} from "@/components/telemetry/impression-tracker";

import type {
  Product,
  RecommendationResponse,
} from "@/types/commerce";


type RecommendationRailProps = {
  data:
    | RecommendationResponse
    | undefined;

  isLoading: boolean;

  onSelect: (
    product: Product
  ) => void;

  onAddToCart: (
    product: Product
  ) => void;

  onImpression: (
    product: Product,
    surface: string
  ) => void | Promise<void>;
};


export function RecommendationRail({
  data,
  isLoading,
  onSelect,
  onAddToCart,
  onImpression,
}: RecommendationRailProps) {
  return (
    <section
      className="recommendation-section"
      id="recommendations"
    >
      <div className="section-heading recommendation-heading">
        <div>
          <span className="eyebrow">
            01 / PERSONALIZED
          </span>

          <h2>
            Recommended
            <br />
            for you.
          </h2>
        </div>

        <div className="recommendation-status">
          <div className="live-state">
            <Radio
              size={14}
              strokeWidth={1.7}
            />

            <span>
              LIVE
            </span>
          </div>

          {data && (
            <>
              <span>
                {data.strategy ===
                "session_intent"
                  ? "SESSION INTENT"
                  : "COLD START"}
              </span>

              <span>
                {
                  data.inference_ms
                }
                {" "}
                MS
              </span>
            </>
          )}
        </div>
      </div>


      <div className="recommendation-note">
        <p>
          {data?.strategy ===
          "session_intent"
            ? "Adapted from your current browsing behavior."
            : "Start exploring and this rail will adapt to your behavior."}
        </p>

        <ArrowRight
          size={18}
          strokeWidth={1.5}
        />
      </div>


      <div className="recommendation-track">
        {isLoading
          ? Array.from({
              length: 5,
            }).map(
              (_, index) => (
                <div
                  className="recommendation-skeleton"
                  key={index}
                />
              )
            )
          : data?.items.map(
              (item) => (
                <div
                  className="recommendation-item"
                  key={
                    item.product
                      .product_id
                  }
                >
                  <ImpressionTracker
                    key={
                      item.product
                        .product_id
                    }
                    product={
                      item.product
                    }
                    surface="recommendation_rail"
                    onImpression={
                      onImpression
                    }
                  >
                    <ProductCard
                      product={
                        item.product
                      }
                      personalized
                      onSelect={
                        onSelect
                      }
                      onAddToCart={
                        onAddToCart
                      }
                    />
                  </ImpressionTracker>
                </div>
              )
            )}
      </div>
    </section>
  );
}