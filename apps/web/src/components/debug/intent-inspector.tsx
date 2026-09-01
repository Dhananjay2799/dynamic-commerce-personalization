"use client";

import {
  Activity,
  BrainCircuit,
  Clock3,
} from "lucide-react";

import type {
  RecommendationResponse,
  SessionIntent,
} from "@/types/commerce";


type IntentInspectorProps = {
  intent:
    | SessionIntent
    | undefined;

  recommendations:
    | RecommendationResponse
    | undefined;
};


export function IntentInspector({
  intent,
  recommendations,
}: IntentInspectorProps) {
  const signals =
    intent
      ?.active_product_signals ??
    [];

  const maximum =
    Math.max(
      ...signals.map(
        (signal) =>
          signal.weight
      ),
      1
    );


  return (
    <aside className="intent-inspector">
      <div className="inspector-header">
        <div>
          <span className="eyebrow">
            DEBUG / LIVE
          </span>

          <h3>
            Intent
            <br />
            Inspector
          </h3>
        </div>

        <BrainCircuit
          size={22}
          strokeWidth={1.4}
        />
      </div>


      <div className="inspector-metrics">
        <div>
          <Activity
            size={14}
          />

          <span>
            Events
          </span>

          <strong>
            {intent?.event_count ??
              0}
          </strong>
        </div>

        <div>
          <Clock3
            size={14}
          />

          <span>
            Inference
          </span>

          <strong>
            {recommendations
              ? `${recommendations.inference_ms} ms`
              : "—"}
          </strong>
        </div>
      </div>


      <div className="inspector-block">
        <span className="inspector-label">
          MODEL
        </span>

        <strong>
          {recommendations
            ?.model_version ??
            "session-svd-v2"}
        </strong>
      </div>


      <div className="inspector-block">
        <span className="inspector-label">
          STRATEGY
        </span>

        <strong>
          {recommendations
            ?.strategy ??
            "waiting"}
        </strong>
      </div>


      <div className="intent-signals">
        <span className="inspector-label">
          ACTIVE PRODUCT SIGNALS
        </span>

        {!signals.length && (
          <p className="inspector-empty">
            No behavioral
            signals yet.
          </p>
        )}

        {signals.map(
          (signal) => {
            const percentage =
              Math.max(
                4,
                (
                  signal.weight /
                  maximum
                ) * 100
              );

            return (
              <div
                className="signal"
                key={
                  signal.product_id
                }
              >
                <div className="signal-copy">
                  <span>
                    #
                    {
                      signal.product_id
                    }
                  </span>

                  <strong>
                    {signal.weight.toFixed(
                      2
                    )}
                  </strong>
                </div>

                <div className="signal-track">
                  <div
                    className="signal-value"
                    style={{
                      width:
                        `${percentage}%`,
                    }}
                  />
                </div>
              </div>
            );
          }
        )}
      </div>
    </aside>
  );
}