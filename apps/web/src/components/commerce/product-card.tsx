"use client";

import {
  ShoppingBag,
  Sparkles,
} from "lucide-react";

import type {
  Product,
} from "@/types/commerce";


type ProductCardProps = {
  product: Product;

  personalized?: boolean;

  onSelect?: (
    product: Product
  ) => void;

  onAddToCart?: (
    product: Product
  ) => void;
};


function formatCategory(
  product: Product
): string {
  if (product.category_leaf) {
    return product.category_leaf;
  }

  if (product.category_l1) {
    return product.category_l1;
  }

  return "collection";
}


function productInitials(
  product: Product
): string {
  const brand =
    product.brand ??
    product.category_leaf ??
    "product";

  return brand
    .slice(0, 2)
    .toUpperCase();
}


export function ProductCard({
  product,
  personalized = false,
  onSelect,
  onAddToCart,
}: ProductCardProps) {
  return (
    <article className="product-card">
      <button
        type="button"
        className="product-card-main"
        onClick={() =>
          onSelect?.(
            product
          )
        }
      >
        <div className="product-media">
          <div className="product-monogram">
            {productInitials(
              product
            )}
          </div>

          {personalized && (
            <div className="personalized-mark">
              <Sparkles
                size={13}
                strokeWidth={1.6}
              />

              <span>
                FOR YOU
              </span>
            </div>
          )}

          <span className="product-id">
            #{product.product_id}
          </span>
        </div>

        <div className="product-copy">
          <div className="product-meta">
            <span>
              {product.brand ??
                "Independent"}
            </span>

            <span>
              {formatCategory(
                product
              )}
            </span>
          </div>

          <h3>
            {product.name}
          </h3>

          <div className="product-price-row">
            <strong>
              $
              {product.price.toLocaleString(
                "en-US",
                {
                  minimumFractionDigits:
                    2,
                  maximumFractionDigits:
                    2,
                }
              )}
            </strong>

            <span>
              {
                product.inventory_quantity
              }{" "}
              available
            </span>
          </div>
        </div>
      </button>

      <button
        type="button"
        className="add-to-cart"
        aria-label={`Add ${product.name} to cart`}
        onClick={() =>
          onAddToCart?.(
            product
          )
        }
      >
        <ShoppingBag
          size={16}
          strokeWidth={1.6}
        />

        Add
      </button>
    </article>
  );
}