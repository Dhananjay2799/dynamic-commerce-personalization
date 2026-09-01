"use client";

import {
  useCallback,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";

import {
  ArrowDown,
  Search,
  Sparkles,
} from "lucide-react";

import {
  PaginationControls,
} from "@/components/commerce/pagination-controls";

import {
  CategoryNav,
} from "@/components/commerce/category-nav";

import {
  ProductDetail,
} from "@/components/commerce/product-detail";

import {
  ProductGrid,
} from "@/components/commerce/product-grid";

import {
  SearchBar,
} from "@/components/commerce/search-bar";

import {
  CartDrawer,
} from "@/components/commerce/cart-drawer";

import {
  IntentInspector,
} from "@/components/debug/intent-inspector";

import {
  RecommendationRail,
} from "@/components/recommendations/recommendation-rail";

import {
  useCategories,
  useProducts,
} from "@/hooks/use-products";

import {
  useRecommendations,
  useSessionIntent,
} from "@/hooks/use-recommendations";

import {
  useTelemetry,
} from "@/hooks/use-telemetry";

import {
  useCart,
} from "@/hooks/use-cart";

import type {
  CartItem,
} from "@/hooks/use-cart";

import type {
  Product,
} from "@/types/commerce";

function getDebugModeSnapshot(): boolean {
  if (
    typeof window ===
    "undefined"
  ) {
    return false;
  }

  const params =
    new URLSearchParams(
      window.location.search
    );

  return (
    params.get("debug") ===
    "true"
  );
}

function getServerDebugModeSnapshot(): boolean {
  return false;
}

function subscribeToUrl(
  callback: () => void
): () => void {
  if (
    typeof window ===
    "undefined"
  ) {
    return () => {};
  }

  window.addEventListener(
    "popstate",
    callback
  );

  return () => {
    window.removeEventListener(
      "popstate",
      callback
    );
  };
}

export default function Home() {
  const [
    selectedCategory,
    setSelectedCategory,
  ] = useState("");

  const [
    productPage,
    setProductPage,
  ] = useState(1);

  const [
    lastSignal,
    setLastSignal,
  ] = useState<
    string | null
  >(null);

  const [
    activeProduct,
    setActiveProduct,
  ] = useState<Product | null>(
    null
  );

  const [
    cartOpen,
    setCartOpen,
  ] = useState(false);

  const {
    items: cartItems,
    itemCount,
    subtotal,
    addItem,
    removeOne,
    removeItem,
  } = useCart();

  const [
    searchInput,
    setSearchInput,
  ] = useState("");

  const [
    searchQuery,
    setSearchQuery,
  ] = useState("");

  const debugMode =
    useSyncExternalStore(
      subscribeToUrl,
      getDebugModeSnapshot,
      getServerDebugModeSnapshot
    );

  const {
    sessionId,
    trackEvent,
  } = useTelemetry();

  const handleProductImpression =
    useCallback(
      async (
        product: Product,
        surface: string
      ) => {
        await trackEvent(
          {
            event_type:
              "product_impression",

            product_id:
              product.product_id,

            category_id:
              product.category_id,

            metadata: {
              surface:
                searchQuery
                  ? "search_results"
                  : surface,

              search_query:
                searchQuery
                  || null,

              brand:
                product.brand,

              category:
                product.category_code,
            },
          },
          {
            refreshRecommendations:
              false,
          }
        );
      },
      [
        trackEvent,
        searchQuery,
      ]
    );

  const productsQuery =
    useProducts(
      selectedCategory,
      searchQuery,
      productPage
    );

  const categoriesQuery =
    useCategories();

  const recommendationsQuery =
    useRecommendations(
      sessionId,
      12
    );

  const intentQuery =
    useSessionIntent(
      sessionId
    );

  const products =
    productsQuery.data
      ?.items ?? [];

  const categories =
    categoriesQuery.data ??
    [];

  const totalProducts =
    useMemo(
      () =>
        productsQuery.data
          ?.total ?? 0,
      [
        productsQuery.data,
      ]
    );

  async function handleSearch() {
    const normalizedQuery =
      searchInput
        .trim()
        .replace(
          /\s+/g,
          " "
        );

    if (!normalizedQuery) {
      setSearchQuery("");
      setProductPage(1);

      return;
    }

    setSearchInput(
      normalizedQuery
    );

    setProductPage(1);

    setSearchQuery(
      normalizedQuery
    );

    setLastSignal(
      `Search intent: ${normalizedQuery}`
    );

    await trackEvent(
      {
        event_type:
          "search",

        metadata: {
          query:
            normalizedQuery,

          query_length:
            normalizedQuery.length,

          surface:
            "storefront_search",
        },
      },
      {
        refreshRecommendations:
          false,
      }
    );
  }

  function handleClearSearch() {
    setSearchInput("");
    setSearchQuery("");
    setProductPage(1);

    setLastSignal(
      "Search cleared"
    );
  }

  async function handleRemoveOne(
    item: CartItem
  ) {
    removeOne(
      item.product
        .product_id
    );

    setLastSignal(
      `Removed one ${item.product.name}`
    );

    await trackEvent({
      event_type:
        "remove_from_cart",

      product_id:
        item.product
          .product_id,

      category_id:
        item.product
          .category_id,

      metadata: {
        surface:
          "cart_drawer",

        quantity_removed:
          1,

        remaining_quantity:
          Math.max(
            0,
            item.quantity
            - 1
          ),
      },
    });
  }

  async function handleRemoveAll(
    item: CartItem
  ) {
    removeItem(
      item.product
        .product_id
    );

    setLastSignal(
      `Removed ${item.product.name} from bag`
    );

    for (
      let index = 0;
      index < item.quantity;
      index += 1
    ) {
      await trackEvent(
        {
          event_type:
            "remove_from_cart",

          product_id:
            item.product
              .product_id,

          category_id:
            item.product
              .category_id,

          metadata: {
            surface:
              "cart_drawer",

            quantity_removed:
              1,

            bulk_remove:
              item.quantity
              > 1,
          },
        },
        {
          refreshRecommendations:
            index
            ===
            item.quantity
            - 1,
        }
      );
    }
  }

  async function handleProductSelect(
    product: Product
  ) {
    setActiveProduct(
      product
    );

    setLastSignal(
      `Viewed ${product.name}`
    );

    await trackEvent({
      event_type:
        "product_click",

      product_id:
        product.product_id,

      category_id:
        product.category_id,

      metadata: {
        surface:
          searchQuery
            ? "search_results"
            : "storefront",

        search_query:
          searchQuery
            || null,

        brand:
          product.brand,

        category:
          product.category_code,
      },
    });
  }

  async function handleAddToCart(
    product: Product
  ) {
    addItem(
      product
    );

    setCartOpen(
      true
    );

    setLastSignal(
      `Added ${product.name} to bag`
    );

    await trackEvent({
      event_type:
        "add_to_cart",

      product_id:
        product.product_id,

      category_id:
        product.category_id,

      metadata: {
        surface:
          activeProduct
            ?.product_id
          ===
          product.product_id
            ? "product_detail"
            : searchQuery
              ? "search_results"
              : "storefront",

        brand:
          product.brand,

        category:
          product.category_code,
      },
    });
  }

  async function handleCategoryChange(
    category: string
  ) {
    setSelectedCategory(
      category
    );

    setProductPage(1);

    const categoryRecord =
      category
        ? categories.find(
            (item) =>
              item.category_l1 ===
              category
          )
        : undefined;

    setLastSignal(
      category
        ? `Category intent: ${category}`
        : "Category intent cleared"
    );

    await trackEvent({
      event_type:
        "category_view",

      category_id:
        categoryRecord
          ?.category_id,

      metadata: {
        category:
          category || null,

        cleared:
          !category,

        surface:
          "category_filter",
      },
    });
  }

  function handlePageChange(
    page: number
  ) {
    setProductPage(
      page
    );

    window.requestAnimationFrame(
      () => {
        document
          .getElementById(
            "explore"
          )
          ?.scrollIntoView({
            behavior:
              "smooth",

            block:
              "start",
          });
      }
    );
  }

  return (
    <main className="commerce-page">
      <header className="site-header">
        <a
          className="brand"
          href="#top"
        >
          PERSONA
        </a>

        <nav className="header-nav">
          <a href="#recommendations">
            For You
          </a>

          <a href="#explore">
            Explore
          </a>
        </nav>

        <div className="header-actions">
          <button
            type="button"
            aria-label="Search"
          >
            <Search
              size={18}
              strokeWidth={1.5}
            />
          </button>

          <button
            type="button"
            className="header-bag-button"
            onClick={() =>
              setCartOpen(
                true
              )
            }
          >
            BAG
            <span>
              {itemCount}
            </span>
          </button>
        </div>
      </header>

      <section
        className="hero"
        id="top"
      >
        <div className="hero-index">
          <span>
            00 / COMMERCE
          </span>

          <span>
            ML-POWERED
          </span>
        </div>

        <div className="hero-copy">
          <div className="hero-kicker">
            <Sparkles
              size={14}
              strokeWidth={1.5}
            />

            <span>
              ADAPTIVE
              SHOPPING
            </span>
          </div>

          <h1>
            COMMERCE,
            <br />

            <span>
              ADAPTED
            </span>

            <br />

            TO YOU.
          </h1>

          <p>
            A storefront that
            learns from every
            interaction and
            re-ranks products
            around your current
            intent.
          </p>
        </div>

        <div className="hero-bottom">
          <a href="#explore">
            EXPLORE
            <ArrowDown
              size={17}
            />
          </a>

          <div>
            <span>
              MODEL
            </span>

            <strong>
              session-svd-v3
            </strong>
          </div>
        </div>
      </section>

      <RecommendationRail
        data={
          recommendationsQuery.data
        }
        isLoading={
          recommendationsQuery
            .isLoading
        }
        isError={
          recommendationsQuery
            .isError
        }
        onRetry={() => {
          void recommendationsQuery
            .refetch();
        }}
        onSelect={
          handleProductSelect
        }
        onAddToCart={
          handleAddToCart
        }
        onImpression={
          handleProductImpression
        }
      />

      <section
        className="explore-section"
        id="explore"
      >
        <div className="section-heading">
          <div>
            <span className="eyebrow">
              02 / DISCOVER
            </span>

            <h2>
              Explore
              <br />
              the catalog.
            </h2>
          </div>

          <div className="catalog-stat">
            <strong>
              {totalProducts.toLocaleString()}
            </strong>

            <span>
              PRODUCTS
            </span>
          </div>
        </div>

        {searchQuery && (
          <div className="search-context">
            <span>
              SEARCH RESULTS
            </span>

            <h3>
              “{searchQuery}”
            </h3>

            <p>
              {productsQuery
                .data
                ?.total
                .toLocaleString()
                ?? 0}
              {" "}
              matching products
            </p>
          </div>
        )}

        <SearchBar
          value={
            searchInput
          }
          resultCount={
            searchQuery
              ? productsQuery
                  .data
                  ?.total
              : undefined
          }
          isSearching={
            productsQuery
              .isFetching
            &&
            Boolean(
              searchQuery
            )
          }
          onChange={
            setSearchInput
          }
          onSubmit={
            handleSearch
          }
          onClear={
            handleClearSearch
          }
        />

        <CategoryNav
          categories={categories}
          selectedCategory={
            selectedCategory
          }
          onChange={
            handleCategoryChange
          }
        />

        {productsQuery.isError ? (
          <div className="catalog-error-state">
            <span>
              CATALOG UNAVAILABLE
            </span>

            <h3>
              We could not load
              this collection.
            </h3>

            <p>
              The storefront is still
              active. Retry the catalog
              request to continue browsing.
            </p>

            <button
              type="button"
              onClick={() => {
                void productsQuery
                  .refetch();
              }}
            >
              RETRY CATALOG
            </button>
          </div>
        ) : (
          <>
            <ProductGrid
              products={products}
              isLoading={
                productsQuery.isLoading
              }
              onSelect={
                handleProductSelect
              }
              onAddToCart={
                handleAddToCart
              }
              onImpression={
                handleProductImpression
              }
            />

            <PaginationControls
              page={
                productsQuery.data
                  ?.page
                ?? productPage
              }
              totalPages={
                productsQuery.data
                  ?.total_pages
                ?? 0
              }
              isFetching={
                productsQuery
                  .isFetching
              }
              onPageChange={
                handlePageChange
              }
            />
          </>
        )}
      </section>

      <footer className="site-footer">
        <div>
          <span>
            REAL-TIME
            PERSONALIZATION
          </span>

          <span>
            FASTAPI / REDIS /
            SVD / NEXT.JS
          </span>
        </div>

        <strong>
          PERSONA
        </strong>
      </footer>

      {lastSignal && (
        <div
          className="signal-toast"
          role="status"
        >
          <span className="toast-dot" />

          {lastSignal}

          <span>
            INTENT UPDATED
          </span>
        </div>
      )}

      {activeProduct && (
        <ProductDetail
          key={
            activeProduct
              .product_id
          }
          product={
            activeProduct
          }
          onClose={() =>
            setActiveProduct(
              null
            )
          }
          onAddToCart={
            handleAddToCart
          }
          trackEvent={
            trackEvent
          }
        />
      )}

      <CartDrawer
        open={
          cartOpen
        }
        items={
          cartItems
        }
        subtotal={
          subtotal
        }
        onClose={() =>
          setCartOpen(
            false
          )
        }
        onRemoveOne={
          handleRemoveOne
        }
        onRemoveAll={
          handleRemoveAll
        }
      />

      {debugMode && (
        <IntentInspector
          intent={
            intentQuery.data
          }
          recommendations={
            recommendationsQuery.data
          }
        />
      )}
    </main>
  );
}