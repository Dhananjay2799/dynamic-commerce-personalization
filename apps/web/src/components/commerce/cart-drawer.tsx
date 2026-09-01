"use client";

import {
  Minus,
  ShoppingBag,
  Trash2,
  X,
} from "lucide-react";

import type {
  CartItem,
} from "@/hooks/use-cart";


type CartDrawerProps = {
  open: boolean;

  items: CartItem[];

  subtotal: number;

  onClose: () => void;

  onRemoveOne: (
    item: CartItem
  ) => void;

  onRemoveAll: (
    item: CartItem
  ) => void;
};


export function CartDrawer({
  open,
  items,
  subtotal,
  onClose,
  onRemoveOne,
  onRemoveAll,
}: CartDrawerProps) {
  if (!open) {
    return null;
  }


  return (
    <div
      className="cart-backdrop"
      onMouseDown={(
        event
      ) => {
        if (
          event.target
          === event.currentTarget
        ) {
          onClose();
        }
      }}
    >
      <aside
        className="cart-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Shopping bag"
      >
        <header className="cart-header">
          <div>
            <span>
              LIVE CART
            </span>

            <h2>
              YOUR BAG
            </h2>
          </div>

          <button
            type="button"
            onClick={
              onClose
            }
            aria-label="Close cart"
          >
            <X
              size={20}
              strokeWidth={1.5}
            />
          </button>
        </header>


        <div className="cart-content">
          {items.length === 0 ? (
            <div className="cart-empty">
              <ShoppingBag
                size={30}
                strokeWidth={1.2}
              />

              <h3>
                YOUR BAG IS EMPTY
              </h3>

              <p>
                Add products and
                watch cart intent
                influence the live
                recommendation model.
              </p>
            </div>
          ) : (
            <div className="cart-items">
              {items.map(
                (item) => (
                  <article
                    className="cart-item"
                    key={
                      item.product
                        .product_id
                    }
                  >
                    <div className="cart-item-visual">
                      <span>
                        {(
                          item.product
                            .brand
                          ??
                          item.product
                            .category_leaf
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


                    <div className="cart-item-copy">
                      <span className="cart-item-brand">
                        {item.product
                          .brand
                          ??
                          "Independent"}
                      </span>

                      <h3>
                        {
                          item.product
                            .name
                        }
                      </h3>

                      <div className="cart-item-bottom">
                        <div>
                          <span>
                            QTY
                          </span>

                          <strong>
                            {
                              item.quantity
                            }
                          </strong>
                        </div>

                        <strong>
                          $
                          {(
                            item.product
                              .price
                            *
                            item.quantity
                          ).toFixed(
                            2
                          )}
                        </strong>
                      </div>


                      <div className="cart-item-actions">
                        <button
                          type="button"
                          onClick={() =>
                            onRemoveOne(
                              item
                            )
                          }
                        >
                          <Minus
                            size={13}
                          />

                          REMOVE ONE
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            onRemoveAll(
                              item
                            )
                          }
                        >
                          <Trash2
                            size={13}
                          />

                          REMOVE ALL
                        </button>
                      </div>
                    </div>
                  </article>
                )
              )}
            </div>
          )}
        </div>


        <footer className="cart-footer">
          <div>
            <span>
              SUBTOTAL
            </span>

            <strong>
              $
              {subtotal.toLocaleString(
                "en-US",
                {
                  minimumFractionDigits:
                    2,

                  maximumFractionDigits:
                    2,
                }
              )}
            </strong>
          </div>

          <button
            type="button"
            disabled={
              items.length
              === 0
            }
          >
            CHECKOUT DEMO
          </button>
        </footer>
      </aside>
    </div>
  );
}