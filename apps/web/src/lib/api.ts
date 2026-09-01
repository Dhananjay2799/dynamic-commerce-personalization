import type {
  Category,
  ProductListResponse,
  RecommendationResponse,
  SessionIntent,
  TelemetryEvent,
} from "@/types/commerce";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

type CategoryListResponse = {
  items: Category[];

  page: number;
  page_size: number;

  total: number;
  total_pages: number;
};

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(
    `${API_URL}${path}`,
    {
      ...options,
      headers: {
        "Content-Type":
          "application/json",
        ...options?.headers,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `API request failed: ${response.status}`
    );
  }

  return response.json();
}

export async function getProducts(
  params?: {
    page?: number;
    pageSize?: number;
    category?: string;
    sort?: string;
    search?: string;
  }
): Promise<ProductListResponse> {
  const search =
    new URLSearchParams();

  search.set(
    "page",
    String(
      params?.page ?? 1
    )
  );

  search.set(
    "page_size",
    String(
      params?.pageSize ?? 24
    )
  );

  if (params?.category) {
    search.set(
      "category",
      params.category
    );
  }

  if (params?.sort) {
    search.set(
      "sort",
      params.sort
    );
  }

  if (params?.search) {
    search.set(
      "search",
      params.search
    );
  }

  return apiFetch(
    `/api/v1/products?${search.toString()}`
  );
}

export async function getCategories(): Promise<Category[]> {
  const pageSize = 100;

  const firstPage =
    await apiFetch<CategoryListResponse>(
      `/api/v1/categories?page=1&page_size=${pageSize}`
    );

  if (
    firstPage.total_pages <= 1
  ) {
    return firstPage.items;
  }

  const remainingPages =
    await Promise.all(
      Array.from(
        {
          length:
            firstPage.total_pages - 1,
        },
        (_, index) =>
          apiFetch<CategoryListResponse>(
            `/api/v1/categories?page=${index + 2}&page_size=${pageSize}`
          )
      )
    );

  return [
    ...firstPage.items,
    ...remainingPages.flatMap(
      (page) =>
        page.items
    ),
  ];
}

export async function sendEvent(
  event: TelemetryEvent
): Promise<void> {
  await apiFetch(
    "/api/v1/events",
    {
      method: "POST",
      body: JSON.stringify(
        event
      ),
    }
  );
}

export async function getRecommendations(
  sessionId: string,
  limit = 12
): Promise<RecommendationResponse> {
  const search =
    new URLSearchParams({
      session_id: sessionId,
      limit: String(limit),
    });

  return apiFetch(
    `/api/v1/recommendations?${search.toString()}`
  );
}

export async function getSessionIntent(
  sessionId: string
): Promise<SessionIntent> {
  return apiFetch(
    `/api/v1/sessions/${sessionId}/intent`
  );
}