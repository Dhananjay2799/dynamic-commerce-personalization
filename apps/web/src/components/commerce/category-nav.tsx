"use client";

import type {
  Category,
} from "@/types/commerce";


type CategoryNavProps = {
  categories: Category[];

  selectedCategory: string;

  onChange: (
    category: string
  ) => void;
};


export function CategoryNav({
  categories,
  selectedCategory,
  onChange,
}: CategoryNavProps) {
  const categoryNames = Array.from(
    new Set(
      categories
        .map(
          (category) =>
            category.category_l1
        )
        .filter(
          (
            value
          ): value is string =>
            Boolean(value)
        )
    )
  ).slice(
    0,
    8
  );


  return (
    <div
      className="category-nav"
      aria-label="Product categories"
    >
      <button
        type="button"
        className={
          selectedCategory === ""
            ? "category-pill active"
            : "category-pill"
        }
        onClick={() =>
          onChange("")
        }
      >
        All
      </button>

      {categoryNames.map(
        (category) => (
          <button
            type="button"
            key={category}
            className={
              selectedCategory ===
              category
                ? "category-pill active"
                : "category-pill"
            }
            onClick={() =>
              onChange(category)
            }
          >
            {category}
          </button>
        )
      )}
    </div>
  );
}