"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  IndianRupee,
  ShieldCheck,
  WalletCards,
  ArrowRight,
  X,
} from "lucide-react";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

type Metrics = {
  total_transactions: number;
  total_money_at_risk: number;
  total_recovered: number;
  recovered_transactions: number;
  failed_recoveries: number;
  pending_recoveries: number;
  recovery_actions: number;
  recovery_rate: number;
  recovery_yield: number;
  recovery_coverage: number;
  state_counts: {
    RECOVERY_LINK_CREATED?: number;
    OUTREACH_PENDING?: number;
    OUTREACH_SENT?: number;
    RETRY_SCHEDULED?: number;
    OPTED_OUT?: number;
  };
};

type ExecutionLog = {
  id: number;
  transaction_id: string;
  previous_state: string | null;
  new_state: string;
  action: string;
  reason: string;
  created_at: string | null;
};

type TransactionDetail = {
  transaction_id: string;
  customer_id: string | null;
  amount: number;
  error_code: string | null;
  failure_type: string | null;
  current_state: string;
  attempt_count: number;
  opt_out: boolean;
  recovery_outcome: string;
  recovered_amount: number;
  original_amount: number | null;
  discounted_amount: number | null;
  payment_link_id: string | null;
  payment_link_url: string | null;
  retry_scheduled_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type TransactionDetailResponse = {
  transaction: TransactionDetail;
  timeline: ExecutionLog[];
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CHART_COLORS = ["#2563eb", "#0f766e", "#b45309", "#6b7280"];

const OUTCOME_COLORS = ["#15803d", "#b91c1c", "#a16207"];

export default function Home() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [engineOnline, setEngineOnline] = useState(false);
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TransactionDetailResponse | null>(
    null
  );
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [optOutLoading, setOptOutLoading] = useState(false);
  const [optOutMessage, setOptOutMessage] = useState("");

  const fetchDashboardData = async () => {
    try {
      setError("");

      const [healthResponse, metricsResponse, logsResponse] =
        await Promise.all([
          fetch(`${API_URL}/`),
          fetch(`${API_URL}/metrics/`),
          fetch(`${API_URL}/metrics/logs?limit=25`),
        ]);

      setEngineOnline(healthResponse.ok);

      if (!metricsResponse.ok || !logsResponse.ok) {
        throw new Error("Failed to fetch dashboard data");
      }

      const metricsData = await metricsResponse.json();
      const logsData = await logsResponse.json();

      setMetrics(metricsData);
      setLogs(logsData.logs || []);
    } catch (err) {
      console.error(err);
      setEngineOnline(false);
      setError("Unable to connect to the recovery engine.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    const interval = setInterval(fetchDashboardData, 10000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!selectedTxnId) {
      setDetail(null);
      setDetailError("");
      setOptOutMessage("");
      return;
    }

    let cancelled = false;

    const loadDetail = async () => {
      setDetailLoading(true);
      setDetailError("");
      setOptOutMessage("");

      try {
        const response = await fetch(
          `${API_URL}/metrics/transactions/${encodeURIComponent(selectedTxnId)}`
        );

        if (!response.ok) {
          throw new Error("Transaction not found");
        }

        const data = await response.json();

        if (!cancelled) {
          setDetail(data);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setDetail(null);
          setDetailError("Unable to load recovery timeline.");
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    };

    loadDetail();

    return () => {
      cancelled = true;
    };
  }, [selectedTxnId]);

  const handleOptOut = async () => {
    if (!selectedTxnId || !detail || detail.transaction.opt_out) {
      return;
    }

    setOptOutLoading(true);
    setOptOutMessage("");

    try {
      const response = await fetch(`${API_URL}/customer/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transaction_id: selectedTxnId,
          message: "STOP",
        }),
      });

      if (!response.ok) {
        throw new Error("Opt-out request failed");
      }

      const body = await response.json();

      if (body.status !== "opted_out") {
        throw new Error(body.message || "Opt-out failed");
      }

      setOptOutMessage("Customer opted out. Recovery halted.");

      const detailResponse = await fetch(
        `${API_URL}/metrics/transactions/${encodeURIComponent(selectedTxnId)}`
      );

      if (detailResponse.ok) {
        setDetail(await detailResponse.json());
      }

      await fetchDashboardData();
    } catch (err) {
      console.error(err);
      setOptOutMessage("Unable to opt out right now. Please try again.");
    } finally {
      setOptOutLoading(false);
    }
  };

  const formatRupees = (paise: number) => {
    return `₹${(paise / 100).toLocaleString("en-IN")}`;
  };

  const formatTime = (value: string | null) => {
    if (!value) return "";
    return new Date(value).toLocaleTimeString();
  };

  const distributionData = metrics
    ? [
        {
          name: "Outreach",
          value:
            (metrics.state_counts.OUTREACH_PENDING || 0) +
            (metrics.state_counts.OUTREACH_SENT || 0),
        },
        {
          name: "Retry",
          value: metrics.state_counts.RETRY_SCHEDULED || 0,
        },
        {
          name: "Payment Links",
          value: metrics.state_counts.RECOVERY_LINK_CREATED || 0,
        },
        {
          name: "Opted Out",
          value: metrics.state_counts.OPTED_OUT || 0,
        },
      ]
    : [];

  const outcomeData = metrics
    ? [
        {
          name: "Recovered",
          value: metrics.recovered_transactions || 0,
        },
        {
          name: "Failed",
          value: metrics.failed_recoveries || 0,
        },
        {
          name: "Pending",
          value: metrics.pending_recoveries || 0,
        },
      ]
    : [];

  const stateRows = [
    {
      key: "OUTREACH_SENT",
      label: "OUTREACH_SENT",
      value: metrics?.state_counts.OUTREACH_SENT || 0,
    },
    {
      key: "OUTREACH_PENDING",
      label: "OUTREACH_PENDING",
      value: metrics?.state_counts.OUTREACH_PENDING || 0,
    },
    {
      key: "RETRY_SCHEDULED",
      label: "RETRY_SCHEDULED",
      value: metrics?.state_counts.RETRY_SCHEDULED || 0,
    },
    {
      key: "RECOVERY_LINK_CREATED",
      label: "RECOVERY_LINK_CREATED",
      value: metrics?.state_counts.RECOVERY_LINK_CREATED || 0,
    },
    {
      key: "OPTED_OUT",
      label: "OPTED_OUT",
      value: metrics?.state_counts.OPTED_OUT || 0,
    },
  ];

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <div className="brand">
            <ShieldCheck size={26} />
            Revenue Recovery Engine
          </div>
          <p className="subtitle">
            Payment failure recovery control center
          </p>
        </div>

        <div className="system-status">
          <span
            className={
              engineOnline ? "status-dot" : "status-dot offline"
            }
          />
          {engineOnline ? "Engine Online" : "Engine Offline"}
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      <section className="metrics-grid metrics-grid-six">
        <MetricCard
          icon={<Activity />}
          label="Transactions"
          value={
            loading
              ? "..."
              : (metrics?.total_transactions ?? 0).toString()
          }
          description="Payment failures ingested"
        />
        <MetricCard
          icon={<IndianRupee />}
          label="Money at Risk"
          value={
            loading
              ? "..."
              : formatRupees(metrics?.total_money_at_risk || 0)
          }
          description="Total transaction value"
        />
        <MetricCard
          icon={<WalletCards />}
          label="Money Recovered"
          value={
            loading
              ? "..."
              : formatRupees(metrics?.total_recovered || 0)
          }
          description="Recovered amount"
        />
        <MetricCard
          icon={<CheckCircle2 />}
          label="Recovery Yield"
          value={`${metrics?.recovery_yield ?? 0}%`}
          description="Recovered / money at risk"
        />
        <MetricCard
          icon={<ShieldCheck />}
          label="Success Rate"
          value={`${metrics?.recovery_rate ?? 0}%`}
          description="Recovered transactions"
        />
        <MetricCard
          icon={<Clock3 />}
          label="Recovery Actions"
          value={
            loading
              ? "..."
              : (metrics?.recovery_actions ?? 0).toString()
          }
          description="Active recovery paths"
        />
      </section>

      <section className="analytics-grid">
        <div className="panel chart-panel">
          <div className="panel-header">
            <div>
              <h2>Recovery Distribution</h2>
              <p>Current recovery actions by type</p>
            </div>
            <WalletCards size={22} />
          </div>

          <div className="chart-container">
            {loading ? (
              <div className="loading">Loading metrics...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={distributionData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                  >
                    {distributionData.map((_, index) => (
                      <Cell
                        key={`dist-${index}`}
                        fill={
                          CHART_COLORS[index % CHART_COLORS.length]
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="panel chart-panel">
          <div className="panel-header">
            <div>
              <h2>Recovery Outcomes</h2>
              <p>Recovered vs failed vs pending</p>
            </div>
            <CheckCircle2 size={22} />
          </div>

          <div className="chart-container">
            {loading ? (
              <div className="loading">Loading outcomes...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={outcomeData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                  >
                    {outcomeData.map((_, index) => (
                      <Cell
                        key={`out-${index}`}
                        fill={
                          OUTCOME_COLORS[
                            index % OUTCOME_COLORS.length
                          ]
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>State Distribution</h2>
              <p>Live engine state counts</p>
            </div>
            <Clock3 size={22} />
          </div>

          <div className="state-list">
            {stateRows.map((row) => (
              <StateRow
                key={row.key}
                label={row.label}
                value={loading ? 0 : row.value}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="panel logs-panel">
        <div className="panel-header">
          <div>
            <h2>Live Execution</h2>
            <p>Click a transaction to inspect its recovery timeline</p>
          </div>
          <div className="live-indicator">
            <span
              className={
                engineOnline ? "status-dot" : "status-dot offline"
              }
            />
            LIVE
          </div>
        </div>

        <div className="logs-list">
          {loading ? (
            <div className="loading">Loading execution logs...</div>
          ) : logs.length === 0 ? (
            <div className="loading">No execution logs available.</div>
          ) : (
            logs.map((log) => (
              <button
                type="button"
                className={`log-row ${
                  selectedTxnId === log.transaction_id
                    ? "log-row-selected"
                    : ""
                }`}
                key={log.id}
                onClick={() => setSelectedTxnId(log.transaction_id)}
              >
                <div className="log-icon">
                  <Activity size={17} />
                </div>

                <div className="log-main">
                  <div className="log-top">
                    <span className="log-time">
                      {formatTime(log.created_at)}
                    </span>
                    <strong>{log.action}</strong>
                  </div>

                  <div className="log-transition">
                    {log.previous_state || "START"}
                    <ArrowRight size={14} />
                    {log.new_state}
                  </div>

                  <div className="log-details">
                    <span className="log-txn">{log.transaction_id}</span>
                    <span>{log.reason}</span>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </section>

      {selectedTxnId && (
        <div
          className="drawer-backdrop"
          onClick={() => setSelectedTxnId(null)}
        >
          <aside
            className="timeline-drawer"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="drawer-header">
              <div>
                <p className="eyebrow">TRANSACTION</p>
                <h2>{selectedTxnId}</h2>
              </div>
              <button
                type="button"
                className="drawer-close"
                onClick={() => setSelectedTxnId(null)}
                aria-label="Close transaction detail"
              >
                <X size={18} />
              </button>
            </div>

            {detailLoading ? (
              <div className="loading">Loading transaction...</div>
            ) : detailError ? (
              <div className="error-banner">{detailError}</div>
            ) : detail ? (
              <>
                <section className="txn-summary">
                  <SummaryRow
                    label="Amount"
                    value={formatRupees(detail.transaction.amount)}
                  />
                  <SummaryRow
                    label="Failure"
                    value={detail.transaction.failure_type || "—"}
                  />
                  <SummaryRow
                    label="Recovery Outcome"
                    value={detail.transaction.recovery_outcome}
                    tone={outcomeTone(
                      detail.transaction.recovery_outcome
                    )}
                  />
                </section>

                <section className="opt-out-panel">
                  <p className="opt-out-help">
                    Simulate a customer STOP reply to halt further recovery
                    for this transaction.
                  </p>
                  <button
                    type="button"
                    className="stop-button"
                    onClick={handleOptOut}
                    disabled={
                      optOutLoading || detail.transaction.opt_out
                    }
                  >
                    {detail.transaction.opt_out
                      ? "Already opted out"
                      : optOutLoading
                        ? "Sending STOP..."
                        : "STOP recovery"}
                  </button>
                  {optOutMessage && (
                    <p
                      className={
                        detail.transaction.opt_out
                          ? "opt-out-status success"
                          : "opt-out-status"
                      }
                    >
                      {optOutMessage}
                    </p>
                  )}
                </section>

                <section className="story-section">
                  <h3>Timeline</h3>
                  <p className="story-subtitle">
                    How this payment failure moved through recovery
                  </p>

                  <ol className="story-timeline">
                    {buildStorySteps(detail).map((step, index, steps) => (
                      <li
                        key={`${step.label}-${index}`}
                        className={`story-step ${
                          index === steps.length - 1
                            ? "story-step-current"
                            : ""
                        }`}
                      >
                        <div className="story-rail" aria-hidden="true">
                          <span className="story-dot" />
                          {index < steps.length - 1 && (
                            <span className="story-line" />
                          )}
                        </div>
                        <div className="story-content">
                          <strong>{step.label}</strong>
                          {step.detail && <span>{step.detail}</span>}
                          {step.time && (
                            <span className="story-time">{step.time}</span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>

                <details className="txn-more">
                  <summary>More details</summary>
                  <div className="detail-grid">
                    <DetailItem
                      label="Current state"
                      value={detail.transaction.current_state}
                    />
                    <DetailItem
                      label="Error code"
                      value={detail.transaction.error_code || "—"}
                    />
                    <DetailItem
                      label="Attempts"
                      value={String(detail.transaction.attempt_count)}
                    />
                    <DetailItem
                      label="Opt out"
                      value={detail.transaction.opt_out ? "Yes" : "No"}
                    />
                    <DetailItem
                      label="Recovered amount"
                      value={formatRupees(
                        detail.transaction.recovered_amount || 0
                      )}
                    />
                    {detail.transaction.discounted_amount != null && (
                      <DetailItem
                        label="Discounted amount"
                        value={formatRupees(
                          detail.transaction.discounted_amount
                        )}
                      />
                    )}
                    {detail.transaction.payment_link_url && (
                      <DetailItem
                        label="Payment link"
                        value={detail.transaction.payment_link_url}
                      />
                    )}
                    {detail.transaction.retry_scheduled_at && (
                      <DetailItem
                        label="Retry at"
                        value={new Date(
                          detail.transaction.retry_scheduled_at
                        ).toLocaleString()}
                      />
                    )}
                  </div>
                </details>
              </>
            ) : null}
          </aside>
        </div>
      )}

      <footer>
        <span>Razorpay Revenue Recovery</span>
        <span>•</span>
        <span>LangGraph Orchestrator</span>
        <span>•</span>
        <span>Safety Guardrails Active</span>
      </footer>
    </main>
  );
}

function MetricCard({
  icon,
  label,
  value,
  description,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  description: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{description}</span>
      </div>
    </div>
  );
}

function StateRow({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="state-row">
      <span className="state-key">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DetailItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="detail-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SummaryRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "success" | "danger" | "warning" | "neutral";
}) {
  return (
    <div className="summary-row">
      <span>{label}</span>
      <strong className={tone ? `summary-${tone}` : undefined}>
        {value}
      </strong>
    </div>
  );
}

function outcomeTone(
  outcome: string
): "success" | "danger" | "warning" | "neutral" {
  if (outcome === "RECOVERED") return "success";
  if (outcome === "FAILED") return "danger";
  if (outcome === "PENDING") return "warning";
  return "neutral";
}

type StoryStep = {
  label: string;
  detail?: string;
  time?: string;
};

function buildStorySteps(detail: TransactionDetailResponse): StoryStep[] {
  const steps: StoryStep[] = [];

  const pushStep = (label: string, detailText?: string, time?: string) => {
    const last = steps[steps.length - 1];
    if (last && last.label === label) {
      return;
    }
    steps.push({
      label,
      detail: detailText,
      time: time
        ? new Date(time).toLocaleTimeString()
        : undefined,
    });
  };

  for (const event of detail.timeline) {
    const stateChanged =
      (event.previous_state || null) !== event.new_state;

    if (stateChanged) {
      pushStep(event.new_state, event.reason || undefined, event.created_at || undefined);
      continue;
    }

    // Same-state events like ATTEMPT_INCREMENTED still matter in the story
    if (event.action && event.action !== "POLICY_CHECK") {
      pushStep(event.action, event.reason || undefined, event.created_at || undefined);
    }
  }

  const outcome = detail.transaction.recovery_outcome;
  if (outcome === "RECOVERED" || outcome === "FAILED") {
    pushStep(outcome);
  }

  if (steps.length === 0) {
    pushStep(detail.transaction.current_state || "RECEIVED");
  }

  return steps;
}
