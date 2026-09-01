"use client";

import {
  useCallback,
  useSyncExternalStore,
} from "react";

import {
  useQueryClient,
} from "@tanstack/react-query";

import {
  sendEvent,
} from "@/lib/api";

import {
  getServerSessionSnapshot,
  getSessionIdSnapshot,
  subscribeToSession,
} from "@/lib/session";

import type {
  TelemetryEvent,
} from "@/types/commerce";


type EventInput = Omit<
  TelemetryEvent,
  "session_id"
>;


export type TrackEventOptions = {
  refreshRecommendations?: boolean;
};


export function useTelemetry() {
  const queryClient =
    useQueryClient();

  const sessionId =
    useSyncExternalStore(
      subscribeToSession,
      getSessionIdSnapshot,
      getServerSessionSnapshot
    );


  const trackEvent =
    useCallback(
      async (
        event: EventInput,
        options:
          TrackEventOptions = {}
      ) => {
        if (!sessionId) {
          return;
        }

        await sendEvent({
          ...event,
          session_id:
            sessionId,
        });

        const shouldRefresh =
          options
            .refreshRecommendations
          ?? true;

        if (!shouldRefresh) {
          return;
        }

        await Promise.all([
          queryClient
            .invalidateQueries({
              queryKey: [
                "recommendations",
                sessionId,
              ],
            }),

          queryClient
            .invalidateQueries({
              queryKey: [
                "session-intent",
                sessionId,
              ],
            }),
        ]);
      },
      [
        queryClient,
        sessionId,
      ]
    );


  return {
    sessionId,
    trackEvent,
  };
}