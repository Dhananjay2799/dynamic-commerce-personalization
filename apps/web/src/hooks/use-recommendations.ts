"use client";

import {
  useQuery,
} from "@tanstack/react-query";

import {
  getRecommendations,
  getSessionIntent,
} from "@/lib/api";


export function useRecommendations(
  sessionId: string,
  limit = 12
) {
  return useQuery({
    queryKey: [
      "recommendations",
      sessionId,
      limit,
    ],

    queryFn: () =>
      getRecommendations(
        sessionId,
        limit
      ),

    enabled: Boolean(sessionId),

    staleTime: 0,
  });
}


export function useSessionIntent(
  sessionId: string
) {
  return useQuery({
    queryKey: [
      "session-intent",
      sessionId,
    ],

    queryFn: () =>
      getSessionIntent(
        sessionId
      ),

    enabled: Boolean(sessionId),

    staleTime: 0,
  });
}