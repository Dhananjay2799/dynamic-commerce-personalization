"use client";

import {
  useQuery,
} from "@tanstack/react-query";

import {
  getCategories,
  getProducts,
} from "@/lib/api";


export function useProducts(
  category?: string,
  search?: string,
  page = 1
) {
  return useQuery({
    queryKey: [
      "products",
      category ?? "all",
      search ?? "",
      page,
    ],

    queryFn: () =>
      getProducts({
        page,
        pageSize: 24,

        category:
          category
          || undefined,

        search:
          search
          || undefined,

        sort: "popular",
      }),
  });
}


export function useCategories() {
  return useQuery({
    queryKey: [
      "categories",
    ],

    queryFn:
      getCategories,

    staleTime:
      5 * 60 * 1000,
  });
}