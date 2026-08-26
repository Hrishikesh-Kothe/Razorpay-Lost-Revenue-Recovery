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
} from "lucide-react";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
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

const API_URL = "http://localhost:8000";

export default function Home() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState<ExecutionLog[]>([]);

  const fetchDashboardData = async () => {
    try {
      setError("");

      const [metricsResponse, logsResponse] = await Promise.all([
        fetch(`${API_URL}/metrics/`),
        fetch(`${API_URL}/metrics/logs?limit=10`),
      ]);

      if (!metricsResponse.ok || !logsResponse.ok) {
        throw new Error("Failed to fetch dashboard data");
      }

      const metricsData = await metricsResponse.json();
      const logsData = await logsResponse.json();

      setMetrics(metricsData);
      setLogs(logsData.logs || []);
    } catch (err) {
      console.error(err);
      setError("Unable to connect to the recovery engine.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    const interval = setInterval(
      fetchDashboardData,
      10000
    );

    return () => clearInterval(interval);
  }, []);

  const formatRupees = (paise: number) => {
    return `₹${(paise / 100).toLocaleString("en-IN")}`;
  };

  const chartData = metrics
    ? [
        {
          name: "Outreach",
          value: metrics.state_counts.OUTREACH_PENDING || 0,
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

  const recoveryCoverage =
    metrics && metrics.total_transactions > 0
      ? (
          (metrics.recovery_actions /
            metrics.total_transactions) *
          100
        ).toFixed(1)
      : "0.0";

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <div className="brand">
            <ShieldCheck size={26} />
            Revenue Recovery Engine
          </div>

          <p className="subtitle">
            AI-powered payment failure recovery control center
          </p>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          Engine Online
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      <section className="hero">
        <div>
          <p className="eyebrow">
            RECOVERY CONTROL CENTER
          </p>

          <h1>
            Recover lost revenue.
            <br />
            Automatically.
          </h1>

          <p className="hero-description">
            Monitor payment failures, enforce recovery
            guardrails, and execute the right recovery
            action automatically.
          </p>
        </div>

        <div className="hero-icon">
          <Activity size={52} />
        </div>
      </section>

      <section className="metrics-grid">
        <MetricCard
          icon={<Activity />}
          label="Transactions Processed"
          value={
            loading
              ? "..."
              : metrics?.total_transactions.toString() || "0"
          }
          description="Total payment failures"
        />

        <MetricCard
          icon={<IndianRupee />}
          label="Money at Risk"
          value={
            loading
              ? "..."
              : formatRupees(
                  metrics?.total_money_at_risk || 0
                )
          }
          description="Transaction value at risk"
        />

        <MetricCard
          icon={<CheckCircle2 />}
          label="Recovery Actions"
          value={
            loading
              ? "..."
              : metrics?.recovery_actions.toString() || "0"
          }
          description="Actions successfully executed"
        />

        <MetricCard
          icon={<WalletCards />}
          label="Money Recovered"
          value={
            loading
              ? "..."
              : formatRupees(
                  metrics?.total_recovered || 0
                )
          }
          description="Recovered through automated recovery"
        />

        <MetricCard
          icon={<CheckCircle2 />}
          label="Recovery Yield"
          value={`${metrics?.recovery_yield ?? 0}%`}
          description="Recovered amount / money at risk"
        />

        <MetricCard
          icon={<ShieldCheck />}
          label="Recovery Success Rate"
          value={`${metrics?.recovery_rate ?? 0}%`}
          description="Recovered transactions"
        />
      </section>

      <section className="content-grid">
        <div className="panel chart-panel">
          <div className="panel-header">
            <div>
              <h2>Recovery Distribution</h2>
              <p>
                Current recovery actions by type
              </p>
            </div>

            <WalletCards size={22} />
          </div>

          <div className="chart-container">
            {loading ? (
              <div className="loading">
                Loading metrics...
              </div>
            ) : (
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={75}
                    outerRadius={120}
                    paddingAngle={3}
                  >
                    {chartData.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                      />
                    ))}
                  </Pie>

                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Recovery States</h2>
              <p>
                Live engine state distribution
              </p>
            </div>

            <Clock3 size={22} />
          </div>

          <div className="state-list">
            <StateRow
              label="Outreach Pending"
              value={
                metrics?.state_counts
                  .OUTREACH_PENDING || 0
              }
            />

            <StateRow
              label="Retry Scheduled"
              value={
                metrics?.state_counts
                  .RETRY_SCHEDULED || 0
              }
            />

            <StateRow
              label="Payment Links Created"
              value={
                metrics?.state_counts
                  .RECOVERY_LINK_CREATED || 0
              }
            />

            <StateRow
              label="Opted Out"
              value={
                metrics?.state_counts
                  .OPTED_OUT || 0
              }
            />
          </div>

          <div className="outcome-summary">
            <OutcomeRow
              label="Recovered"
              value={
                metrics?.recovered_transactions || 0
              }
            />

            <OutcomeRow
              label="Failed"
              value={
                metrics?.failed_recoveries || 0
              }
            />

            <OutcomeRow
              label="Pending"
              value={
                metrics?.pending_recoveries || 0
              }
            />
          </div>
        </div>
      </section>

      <section className="panel logs-panel">
        <div className="panel-header">
          <div>
            <h2>Live Execution Log</h2>
            <p>
              Real-time recovery engine activity
            </p>
          </div>

          <div className="live-indicator">
            <span className="status-dot" />
            LIVE
          </div>
        </div>

        <div className="logs-list">
          {loading ? (
            <div className="loading">
              Loading execution logs...
            </div>
          ) : logs.length === 0 ? (
            <div className="loading">
              No execution logs available.
            </div>
          ) : (
            logs.map((log) => (
              <div
                className="log-row"
                key={log.id}
              >
                <div className="log-icon">
                  <Activity size={17} />
                </div>

                <div className="log-main">
                  <div className="log-top">
                    <strong>
                      {log.action}
                    </strong>

                    <span className="log-time">
                      {log.created_at
                        ? new Date(
                            log.created_at
                          ).toLocaleTimeString()
                        : ""}
                    </span>
                  </div>

                  <div className="log-transition">
                    {log.previous_state ||
                      "START"}

                    <ArrowRight size={14} />

                    {log.new_state}
                  </div>

                  <div className="log-details">
                    <span>
                      {log.transaction_id}
                    </span>

                    <span>
                      {log.reason}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

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
      <div className="metric-icon">
        {icon}
      </div>

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
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function OutcomeRow({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="state-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
} 