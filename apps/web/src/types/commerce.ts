export type Product = {
  product_id: number;
  category_id: number;
  name: string;

  category_code: string | null;
  category_l1: string | null;
  category_leaf: string | null;

  brand: string | null;

  price: number;
  inventory_quantity: number;
  image_url: string | null;

  total_events: number;
  views: number;
  carts: number;
  purchases: number;

  view_to_purchase_rate: number;
  view_to_cart_rate: number;

  last_event_time: string;
};

export type ProductListResponse = {
  items: Product[];

  page: number;
  page_size: number;

  total: number;
  total_pages: number;
};

export type Category = {
  category_id: number;

  category_code: string | null;
  category_l1: string | null;
  category_leaf: string | null;

  total_events: number;
  views: number;
  carts: number;
  purchases: number;

  unique_products: number;
  unique_users: number;

  view_to_purchase_rate: number;
};

export type RecommendationItem = {
  product: Product;

  score: number;
  reason: string;
};

export type RecommendationResponse = {
  session_id: string;

  strategy:
    | "popularity"
    | "session_intent";

  model_version: string;

  inference_ms: number;
  total_ms: number;

  items: RecommendationItem[];
};

export type IntentSignal = {
  product_id: number;
  weight: number;
};

export type SessionIntent = {
  session_id: string;

  event_count: number;

  active_product_signals: IntentSignal[];

  model_version: string;
};

export type TelemetryEventType =
  | "product_impression"
  | "view_item"
  | "product_click"
  | "dwell_time"
  | "scroll_depth"
  | "add_to_cart"
  | "remove_from_cart"
  | "purchase"
  | "category_view"
  | "search";

export type TelemetryEvent = {
  session_id: string;

  event_type: TelemetryEventType;

  product_id?: number;
  category_id?: number;

  metadata?: Record<
    string,
    unknown
  >;
};