"use client";

import {
  useCallback,
  useMemo,
  useState,
} from "react";

import type {
  Product,
} from "@/types/commerce";


export type CartItem = {
  product: Product;
  quantity: number;
};


export function useCart() {
  const [
    items,
    setItems,
  ] = useState<CartItem[]>([]);


  const addItem =
    useCallback(
      (
        product: Product
      ) => {
        setItems(
          (currentItems) => {
            const existing =
              currentItems.find(
                (item) =>
                  item.product
                    .product_id
                  ===
                  product.product_id
              );

            if (existing) {
              return currentItems.map(
                (item) =>
                  item.product
                    .product_id
                  ===
                  product.product_id
                    ? {
                        ...item,
                        quantity:
                          item.quantity
                          + 1,
                      }
                    : item
              );
            }

            return [
              ...currentItems,
              {
                product,
                quantity: 1,
              },
            ];
          }
        );
      },
      []
    );


  const removeOne =
    useCallback(
      (
        productId: number
      ) => {
        setItems(
          (currentItems) =>
            currentItems
              .map(
                (item) => {
                  if (
                    item.product
                      .product_id
                    !==
                    productId
                  ) {
                    return item;
                  }

                  return {
                    ...item,
                    quantity:
                      item.quantity
                      - 1,
                  };
                }
              )
              .filter(
                (item) =>
                  item.quantity
                  > 0
              )
        );
      },
      []
    );


  const removeItem =
    useCallback(
      (
        productId: number
      ) => {
        setItems(
          (currentItems) =>
            currentItems.filter(
              (item) =>
                item.product
                  .product_id
                !==
                productId
            )
        );
      },
      []
    );


  const itemCount =
    useMemo(
      () =>
        items.reduce(
          (
            total,
            item
          ) =>
            total
            + item.quantity,
          0
        ),
      [items]
    );


  const subtotal =
    useMemo(
      () =>
        items.reduce(
          (
            total,
            item
          ) =>
            total
            +
            item.product.price
            * item.quantity,
          0
        ),
      [items]
    );


  return {
    items,
    itemCount,
    subtotal,
    addItem,
    removeOne,
    removeItem,
  };
}