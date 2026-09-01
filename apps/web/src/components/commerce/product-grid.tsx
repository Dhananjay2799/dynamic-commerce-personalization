"use client";

import {
  ProductCard,
} from "@/components/commerce/product-card";

import {
  ImpressionTracker,
} from "@/components/telemetry/impression-tracker";

import type {
  Product,
} from "@/types/commerce";


type ProductGridProps = {
  products: Product[];

  isLoading?: boolean;

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


function ProductSkeleton() {
  return (
    <div className="product-card skeleton-card">
      <div className="skeleton-media" />

      <div className="skeleton-copy">
        <div className="skeleton-line short" />
        <div className="skeleton-line" />
        <div className="skeleton-line medium" />
      </div>
    </div>
  );
}


export function ProductGrid({
  products,
  isLoading,
  onSelect,
  onAddToCart,
  onImpression,
}: ProductGridProps) {
  if (isLoading) {
    return (
      <div className="product-grid">
        {Array.from({
          length: 8,
        }).map(
          (_, index) => (
            <ProductSkeleton
              key={index}
            />
          )
        )}
      </div>
    );
  }


  if (!products.length) {
    return (
      <div className="empty-state">
        <span>NO PRODUCTS</span>

        <h3>
          Nothing matched this
          collection.
        </h3>
      </div>
    );
  }


  return (
    <div className="product-grid">
      {products.map(
        (product) => (
          <ImpressionTracker
            key={
              product.product_id
            }
            product={
              product
            }
            surface="explore_grid"
            onImpression={
              onImpression
            }
          >
            <ProductCard
              product={
                product
              }
              onSelect={
                onSelect
              }
              onAddToCart={
                onAddToCart
              }
            />
          </ImpressionTracker>
        )
      )}
    </div>
  );
}