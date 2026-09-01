"use client";

import {
  ArrowLeft,
  ArrowRight,
} from "lucide-react";


type PaginationControlsProps = {
  page: number;
  totalPages: number;
  isFetching?: boolean;

  onPageChange: (
    page: number
  ) => void;
};


export function PaginationControls({
  page,
  totalPages,
  isFetching = false,
  onPageChange,
}: PaginationControlsProps) {
  if (totalPages <= 1) {
    return null;
  }

  const canGoBack =
    page > 1;

  const canGoForward =
    page < totalPages;

  return (
    <nav
      className="catalog-pagination"
      aria-label="Catalog pagination"
    >
      <button
        type="button"
        disabled={
          !canGoBack
          || isFetching
        }
        onClick={() =>
          onPageChange(
            page - 1
          )
        }
      >
        <ArrowLeft
          size={15}
          strokeWidth={1.5}
        />

        PREVIOUS
      </button>

      <div className="pagination-status">
        <span>
          PAGE
        </span>

        <strong>
          {page}
        </strong>

        <span>
          OF
        </span>

        <strong>
          {totalPages}
        </strong>
      </div>

      <button
        type="button"
        disabled={
          !canGoForward
          || isFetching
        }
        onClick={() =>
          onPageChange(
            page + 1
          )
        }
      >
        NEXT

        <ArrowRight
          size={15}
          strokeWidth={1.5}
        />
      </button>
    </nav>
  );
}