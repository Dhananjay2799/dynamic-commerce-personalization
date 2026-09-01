"use client";

import {
  useEffect,
  useRef,
} from "react";

import type {
  ReactNode,
} from "react";

import type {
  Product,
} from "@/types/commerce";


const seenImpressions =
  new Set<string>();


type ImpressionTrackerProps = {
  product: Product;

  surface: string;

  children: ReactNode;

  onImpression: (
    product: Product,
    surface: string
  ) => void | Promise<void>;
};


export function ImpressionTracker({
  product,
  surface,
  children,
  onImpression,
}: ImpressionTrackerProps) {
  const containerRef =
    useRef<HTMLDivElement>(
      null
    );


  useEffect(() => {
    const element =
      containerRef.current;

    if (!element) {
      return;
    }

    const impressionKey =
      `${surface}:${product.product_id}`;

    if (
      seenImpressions.has(
        impressionKey
      )
    ) {
      return;
    }

    let visibilityTimer:
      ReturnType<
        typeof setTimeout
      >
      | null = null;


    const observer =
      new IntersectionObserver(
        ([entry]) => {
          const visible =
            entry.isIntersecting
            &&
            entry.intersectionRatio
              >= 0.5;

          if (visible) {
            if (
              visibilityTimer
            ) {
              return;
            }

            visibilityTimer =
              setTimeout(
                () => {
                  seenImpressions.add(
                    impressionKey
                  );

                  void onImpression(
                    product,
                    surface
                  );

                  observer.unobserve(
                    element
                  );

                  visibilityTimer =
                    null;
                },
                500
              );

            return;
          }

          if (
            visibilityTimer
          ) {
            clearTimeout(
              visibilityTimer
            );

            visibilityTimer =
              null;
          }
        },
        {
          threshold: [
            0,
            0.5,
            1,
          ],
        }
      );


    observer.observe(
      element
    );


    return () => {
      if (
        visibilityTimer
      ) {
        clearTimeout(
          visibilityTimer
        );
      }

      observer.disconnect();
    };
  }, [
    onImpression,
    product,
    surface,
  ]);


  return (
    <div
      ref={
        containerRef
      }
    >
      {children}
    </div>
  );
}