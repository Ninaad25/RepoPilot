import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Search,
  Code2,
  Package,
  Cpu,
  Server,
  Terminal,
  FileCode2,
  FolderTree,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Rocket,
  XCircle,
  Box,
  ExternalLink,
} from "lucide-react";

import "../App.css";

const API_URL = "http://127.0.0.1:8000";

axios.defaults.headers.common["Authorization"] =
  `Bearer ${localStorage.getItem("repopilot_token")}`;

function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [sandbox, setSandbox] = useState(null);
  const [error, setError] = useState("");

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [analysis, setAnalysis] = useState(null);

  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("repopilot_token");
    localStorage.removeItem("repopilot_user");

    delete axios.defaults.headers.common["Authorization"];

    navigate("/login");
  };

  const analyzeRepository = async () => {
    if (!repoUrl.trim()) {
      setAnalysisError("Please enter a GitHub repository URL.");
      return;
    }

    setAnalysisLoading(true);
    setAnalysisError("");
    setAnalysis(null);

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/api/repository/analyze",
        {
          url: repoUrl.trim(),
        },
      );

      setAnalysis(response.data.analysis);
    } catch (error) {
      const message =
        error?.response?.data?.detail || "Unable to analyze repository.";

      setAnalysisError(message);
    } finally {
      setAnalysisLoading(false);
    }
  };

  // ==================================================
  // POLL SANDBOX STATUS
  // ==================================================

  useEffect(() => {
    if (!sandbox?.sandbox_id) {
      return;
    }

    const pollStatus = async () => {
      try {
        const response = await axios.get(
          `${API_URL}/api/sandbox/${sandbox.sandbox_id}`,
        );

        const data = response.data;

        if (data?.sandbox) {
          setSandbox((current) => ({
            ...current,
            ...data.sandbox,
            preview_url: data.preview_url || current?.preview_url,
          }));
        }
      } catch (err) {
        console.error("Unable to fetch sandbox status:", err);
      }
    };

    pollStatus();

    const interval = setInterval(pollStatus, 3000);

    return () => clearInterval(interval);
  }, [sandbox?.sandbox_id]);

  // ==================================================
  // LAUNCH REPOSITORY
  // ==================================================

  const launchRepository = async () => {
    if (!repoUrl.trim()) {
      setError("Please enter a GitHub repository URL.");
      return;
    }

    setLoading(true);
    setError("");
    setSandbox(null);

    try {
      const response = await axios.post(`${API_URL}/api/sandbox/launch`, {
        url: repoUrl.trim(),
      });

      setSandbox(response.data);
    } catch (err) {
      console.error(err);

      const message =
        err.response?.data?.detail || "Unable to launch repository.";

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // ==================================================
  // FORM SUBMIT
  // ==================================================

  const handleSubmit = (event) => {
    event.preventDefault();
    launchRepository();
  };

  // ==================================================
  // STATUS
  // ==================================================

  const status = sandbox?.status;

  const isRunning = status === "RUNNING";

  const isStopped =
    status === "STOPPED" || status === "DEAD" || status === "NOT_FOUND";

  return (
    <div className="app">
      {/* Background effects */}
      <div className="background-glow glow-one" />
      <div className="background-glow glow-two" />

      {/* ================================================
          NAVBAR
      ================================================= */}

      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Rocket size={20} />
          </div>

          <span>RepoPilot</span>
        </div>

        <div className="status-pill">
          <span className={`status-dot ${isStopped ? "offline" : ""}`} />

          {isStopped ? "Sandbox Offline" : "Sandbox Engine Online"}
        </div>
        <button type="button" className="logout-button" onClick={handleLogout}>
          Sign out
        </button>
      </header>

      {/* ================================================
          MAIN
      ================================================= */}

      <main className="main">
        {/* ==============================================
            HERO
        =============================================== */}

        <section className="hero">
          <div className="hero-badge">
            <Terminal size={15} />
            GitHub → Live Demo
          </div>

          <h1>
            Turn any repository into a<span> live demo.</span>
          </h1>

          <p className="hero-description">
            Paste a GitHub repository and RepoPilot automatically analyzes,
            builds, and launches it inside an isolated Docker sandbox.
          </p>

          {/* Launch form */}

          <form className="launch-form" onSubmit={handleSubmit}>
            <div className="input-wrapper">
              <Terminal size={20} />

              <input
                type="url"
                placeholder="https://github.com/username/repository"
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                disabled={loading}
              />
            </div>

            <button type="submit" className="launch-button" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={18} className="spin" />
                  Launching...
                </>
              ) : (
                <>
                  <Rocket size={18} />
                  Launch Demo
                </>
              )}
            </button>
          </form>

          {/* Error */}

          {error && (
            <div className="error-message">
              <XCircle size={18} />

              <span>{error}</span>
            </div>
          )}
        </section>

        {/* ==============================================
            LOADING
        =============================================== */}

        {loading && (
          <section className="progress-card">
            <div className="progress-header">
              <div>
                <p className="eyebrow">SANDBOX DEPLOYMENT</p>

                <h2>Preparing your repository</h2>
              </div>

              <Loader2 size={24} className="spin" />
            </div>

            <div className="progress-list">
              <ProgressItem
                icon={<Terminal size={17} />}
                text="Cloning repository"
                active
              />

              <ProgressItem
                icon={<Box size={17} />}
                text="Building Docker sandbox"
                active
              />

              <ProgressItem
                icon={<Server size={17} />}
                text="Starting preview server"
                active
              />
            </div>
          </section>
        )}

        {/* ==============================================
            RESULT
        =============================================== */}

        {sandbox && !loading && (
          <section className="result-card">
            {/* Success banner */}

            <div className={`success-banner ${isStopped ? "stopped" : ""}`}>
              {isStopped ? <XCircle size={21} /> : <CheckCircle2 size={21} />}

              <div>
                <strong>
                  {isRunning ? "Sandbox is live" : "Sandbox is offline"}
                </strong>

                <span>
                  {isRunning
                    ? "Your repository is running successfully."
                    : "The Docker container is no longer running."}
                </span>
              </div>
            </div>

            {/* Information */}

            <div className="result-grid">
              <InfoCard
                label="Sandbox"
                value={sandbox.sandbox_id || "Unknown"}
              />

              <InfoCard
                label="Container"
                value={sandbox.container_id || "Unknown"}
              />

              <InfoCard
                label="Status"
                value={sandbox.status || "UNKNOWN"}
                status={isRunning}
              />
            </div>

            <div className="analysis-panel">
              <div className="analysis-header">
                <div>
                  <div className="analysis-eyebrow">
                    REPOSITORY INTELLIGENCE
                  </div>

                  <h2>Repository Analysis</h2>

                  <p>
                    Inspect the repository before launching its sandbox
                    environment.
                  </p>
                </div>

                <button
                  className="analysis-button"
                  onClick={analyzeRepository}
                  disabled={analysisLoading}
                >
                  {analysisLoading ? (
                    <>
                      <Loader2 size={18} className="spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Search size={18} />
                      Analyze Repository
                    </>
                  )}
                </button>
              </div>

              {analysisError && (
                <div className="analysis-error">
                  <AlertCircle size={18} />

                  <span>{analysisError}</span>
                </div>
              )}

              {analysisLoading && (
                <div className="analysis-loading">
                  <Loader2 size={32} className="spin" />

                  <div>
                    <strong>Analyzing repository</strong>

                    <p>
                      Detecting framework, runtime, dependencies and project
                      structure...
                    </p>
                  </div>
                </div>
              )}

              {analysis && (
                <div className="analysis-results">
                  {/* PROJECT */}

                  <div className="analysis-card">
                    <div className="analysis-card-title">
                      <Code2 size={20} />

                      <span>Project</span>
                    </div>

                    <div className="analysis-grid">
                      <div>
                        <span>Framework</span>

                        <strong>
                          {analysis.project?.framework || "Unknown"}
                        </strong>
                      </div>

                      <div>
                        <span>Language</span>

                        <strong>
                          {analysis.project?.language || "Unknown"}
                        </strong>
                      </div>
                    </div>
                  </div>

                  {/* RUNTIME */}

                  <div className="analysis-card">
                    <div className="analysis-card-title">
                      <Cpu size={20} />

                      <span>Runtime</span>
                    </div>

                    <div className="analysis-grid">
                      <div>
                        <span>Runtime</span>

                        <strong>
                          {analysis.runtime?.runtime || "Unknown"}
                        </strong>
                      </div>

                      <div>
                        <span>Port</span>

                        <strong>
                          {analysis.runtime?.port ||
                            analysis.runtime_detection?.port ||
                            "Unknown"}
                        </strong>
                      </div>

                      <div>
                        <span>Package Manager</span>

                        <strong>{analysis.package_manager || "Unknown"}</strong>
                      </div>
                    </div>
                  </div>

                  {/* COMMANDS */}

                  <div className="analysis-card">
                    <div className="analysis-card-title">
                      <Terminal size={20} />

                      <span>Commands</span>
                    </div>

                    <div className="command-list">
                      <div>
                        <span>Build</span>

                        <code>
                          {analysis.runtime?.build_command || "Not detected"}
                        </code>
                      </div>

                      <div>
                        <span>Start</span>

                        <code>
                          {analysis.runtime?.start_command || "Not detected"}
                        </code>
                      </div>
                    </div>
                  </div>

                  {/* DEPENDENCIES */}

                  <div className="analysis-card">
                    <div className="analysis-card-title">
                      <Package size={20} />

                      <span>Dependencies</span>
                    </div>

                    {analysis.dependencies?.length ? (
                      <div className="dependency-list">
                        {analysis.dependencies
                          .slice(0, 20)
                          .map((dependency) => (
                            <div
                              className="dependency-item"
                              key={`${dependency.type}-${dependency.name}`}
                            >
                              <span>{dependency.name}</span>

                              <code>{dependency.version}</code>
                            </div>
                          ))}
                      </div>
                    ) : (
                      <div className="empty-analysis">
                        No package dependencies detected.
                      </div>
                    )}
                  </div>

                  {/* FILE STRUCTURE */}

                  <div className="analysis-card">
                    <div className="analysis-card-title">
                      <FolderTree size={20} />

                      <span>Project Structure</span>
                    </div>

                    <div className="structure-list">
                      {analysis.structure?.length ? (
                        analysis.structure.map((item) => (
                          <div className="structure-item" key={item}>
                            <FileCode2 size={16} />
                            {item}
                          </div>
                        ))
                      ) : (
                        <div className="empty-analysis">
                          No directories detected.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Preview */}

            {sandbox.preview_url && (
              <>
                <a
                  href={sandbox.preview_url}
                  target="_blank"
                  rel="noreferrer"
                  className="preview-button"
                >
                  <ExternalLink size={18} />
                  Open Live Preview
                </a>

                <p className="preview-url">{sandbox.preview_url}</p>
              </>
            )}
          </section>
        )}

        {/* ==============================================
            FEATURES
        =============================================== */}

        <section className="features">
          <Feature
            icon={<Terminal size={21} />}
            title="Any GitHub Repository"
            description="Point RepoPilot at a public repository and let it analyze the project automatically."
          />

          <Feature
            icon={<Box size={21} />}
            title="Isolated Docker Sandbox"
            description="Every project runs inside its own resource-limited container."
          />

          <Feature
            icon={<Rocket size={21} />}
            title="Instant Preview"
            description="Get a preview URL as soon as the application starts."
          />
        </section>
      </main>

      {/* ================================================
          FOOTER
      ================================================= */}

      <footer>
        <span>RepoPilot</span>

        <span className="footer-dot">•</span>

        <span>AI-powered repository demos</span>
      </footer>
    </div>
  );
}

// ======================================================
// PROGRESS ITEM
// ======================================================

function ProgressItem({ icon, text, active }) {
  return (
    <div className="progress-item">
      <div className={`progress-icon ${active ? "active" : ""}`}>
        {active ? <Loader2 size={16} className="spin" /> : icon}
      </div>

      <span>{text}</span>
    </div>
  );
}

// ======================================================
// INFO CARD
// ======================================================

function InfoCard({ label, value, status }) {
  return (
    <div className="info-card">
      <span>{label}</span>

      <strong className={status ? "live" : ""}>
        {status && <span className="mini-dot" />}

        {value}
      </strong>
    </div>
  );
}

// ======================================================
// FEATURE
// ======================================================

function Feature({ icon, title, description }) {
  return (
    <div className="feature">
      <div className="feature-icon">{icon}</div>

      <h3>{title}</h3>

      <p>{description}</p>
    </div>
  );
}

export default App;
