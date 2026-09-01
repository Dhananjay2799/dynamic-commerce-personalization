"use client";

import {
  Search,
  X,
} from "lucide-react";

import type {
  FormEvent,
} from "react";


type SearchBarProps = {
  value: string;

  resultCount?: number;

  isSearching?: boolean;

  onChange: (
    value: string
  ) => void;

  onSubmit: () => void;

  onClear: () => void;
};


export function SearchBar({
  value,
  resultCount,
  isSearching = false,
  onChange,
  onSubmit,
  onClear,
}: SearchBarProps) {
  function handleSubmit(
    event:
      FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    onSubmit();
  }


  return (
    <form
      className="commerce-search"
      onSubmit={
        handleSubmit
      }
    >
      <div className="commerce-search-icon">
        <Search
          size={17}
          strokeWidth={1.4}
        />
      </div>


      <input
        type="search"
        value={value}
        onChange={(
          event
        ) =>
          onChange(
            event.target.value
          )
        }
        placeholder="SEARCH PRODUCTS, BRANDS, CATEGORIES"
        aria-label="Search products"
        autoComplete="off"
      />


      <div className="commerce-search-status">
        {isSearching ? (
          <span>
            SEARCHING
          </span>
        ) : (
          resultCount !==
            undefined && (
            <span>
              {resultCount
                .toLocaleString()}
              {" "}
              RESULTS
            </span>
          )
        )}
      </div>


      {value && (
        <button
          className="commerce-search-clear"
          type="button"
          onClick={
            onClear
          }
          aria-label="Clear search"
        >
          <X
            size={16}
            strokeWidth={1.4}
          />
        </button>
      )}


      <button
        className="commerce-search-submit"
        type="submit"
      >
        SEARCH
      </button>
    </form>
  );
}