import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

import {
  Search,
  Code2,
  Package,
  Terminal,
  FileCode2,
  FolderTree,
  Loader2,
  AlertCircle,
  Rocket,
  Box,
  ExternalLink,
  Server,
  CheckCircle2,
  XCircle,
} from "lucide-react";

import "../App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/*
|--------------------------------------------------------------------------
| Axios authentication
|--------------------------------------------------------------------------
*/

const token = localStorage.getItem("repopilot_token");

if (token) {
  axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
}

/*
|--------------------------------------------------------------------------
| Dashboard
|--------------------------------------------------------------------------
*/

function Dashboard() {
  const navigate = useNavigate();

  const [repoUrl, setRepoUrl] = useState("");

  const [loading, setLoading] = useState(false);
  const [sandbox, setSandbox] = useState(null);
  const [error, setError] = useState("");

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [analysis, setAnalysis] = useState(null);

  /*
  |--------------------------------------------------------------------------
  | Logout
  |--------------------------------------------------------------------------
  */

  const handleLogout = () => {
    localStorage.removeItem("repopilot_token");
    localStorage.removeItem("repopilot_user");

    delete axios.defaults.headers.common["Authorization"];

    navigate("/login");
  };

  /*
  |--------------------------------------------------------------------------
  | Analyze repository
  |--------------------------------------------------------------------------
  */

  const analyzeRepository = async () => {
    if (!repoUrl.trim()) {
      setAnalysisError("Please enter a GitHub repository URL.");
      return;
    }

    setAnalysisLoading(true);
    setAnalysisError("");
    setAnalysis(null);

    try {
      const response = await axios.post(`${API_URL}/api/repository/analyze`, {
        url: repoUrl.trim(),
      });

      console.log("Repository analysis:", response.data);

      setAnalysis(response.data.analysis);
    } catch (err) {
      console.error("Repository analysis failed:", err);

      if (err.response?.status === 401) {
        localStorage.removeItem("repopilot_token");
        localStorage.removeItem("repopilot_user");

        delete axios.defaults.headers.common["Authorization"];

        navigate("/login");
        return;
      }

      const message =
        err?.response?.data?.detail || "Unable to analyze repository.";

      setAnalysisError(message);
    } finally {
      setAnalysisLoading(false);
    }
  };

  /*
  |--------------------------------------------------------------------------
  | Poll sandbox status
  |--------------------------------------------------------------------------
  */

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

  /*
  |--------------------------------------------------------------------------
  | Launch repository
  |--------------------------------------------------------------------------
  */

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

      console.log("Sandbox launch response:", response.data);

      setSandbox(response.data);
    } catch (err) {
      console.error("Sandbox launch failed:", err);

      if (err.response?.status === 401) {
        localStorage.removeItem("repopilot_token");
        localStorage.removeItem("repopilot_user");

        delete axios.defaults.headers.common["Authorization"];

        navigate("/login");
        return;
      }

      const message =
        err?.response?.data?.detail || "Unable to launch repository.";

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  /*
  |--------------------------------------------------------------------------
  | Form submit
  |--------------------------------------------------------------------------
  */

  const handleSubmit = (event) => {
    event.preventDefault();

    launchRepository();
  };

  /*
  |--------------------------------------------------------------------------
  | Sandbox status
  |--------------------------------------------------------------------------
  */

  const status = sandbox?.status;

  const isRunning = status === "RUNNING";

  const isStopped =
    status === "STOPPED" || status === "DEAD" || status === "NOT_FOUND";

  /*
  |--------------------------------------------------------------------------
  | Render
  |--------------------------------------------------------------------------
  */

  return (
    <div className="app">
      {/* Background effects */}

      <div className="background-glow glow-one" />
      <div className="background-glow glow-two" />

      {/* ==================================================
          NAVBAR
      ================================================== */}

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

      {/* ==================================================
          MAIN
      ================================================== */}

      <main className="main">
        {/* ==================================================
            HERO
        ================================================== */}

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

          {/* ==================================================
              LAUNCH FORM
          ================================================== */}

          <form className="repo-form" onSubmit={handleSubmit}>
            <div className="repo-input-wrapper">
              <Search size={20} />

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
                  Launch Sandbox
                </>
              )}
            </button>
          </form>

          {/* ==================================================
              LAUNCH ERROR
          ================================================== */}

          {error && (
            <div className="launch-error">
              <AlertCircle size={18} />

              <span>{error}</span>
            </div>
          )}

          {/* ==================================================
              SANDBOX STATUS
          ================================================== */}

          {sandbox && (
            <div className="sandbox-status">
              <div className="sandbox-status-header">
                <div>
                  <div className="analysis-eyebrow">SANDBOX</div>

                  <h3>Sandbox Environment</h3>
                </div>

                <div
                  className={`sandbox-state ${
                    isRunning ? "running" : isStopped ? "stopped" : ""
                  }`}
                >
                  {isRunning ? (
                    <>
                      <CheckCircle2 size={16} />
                      Running
                    </>
                  ) : isStopped ? (
                    <>
                      <XCircle size={16} />
                      Stopped
                    </>
                  ) : (
                    <>
                      <Loader2 size={16} className="spin" />
                      {status || "Starting"}
                    </>
                  )}
                </div>
              </div>

              <div className="analysis-grid">
                <div>
                  <span>Sandbox ID</span>

                  <strong>{sandbox.sandbox_id || "Unknown"}</strong>
                </div>

                <div>
                  <span>Container</span>

                  <strong>{sandbox.container_name || "Unknown"}</strong>
                </div>

                <div>
                  <span>Port</span>

                  <strong>{sandbox.host_port || "Unknown"}</strong>
                </div>
              </div>
            </div>
          )}

          {/* ==================================================
              REPOSITORY ANALYSIS
          ================================================== */}

          <div className="analysis-panel">
            <div className="analysis-header">
              <div>
                <div className="analysis-eyebrow">REPOSITORY INTELLIGENCE</div>

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

            {/* ==================================================
                ANALYSIS ERROR
            ================================================== */}

            {analysisError && (
              <div className="analysis-error">
                <AlertCircle size={18} />

                <span>{analysisError}</span>
              </div>
            )}

            {/* ==================================================
                ANALYSIS LOADING
            ================================================== */}

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

            {/* ==================================================
                ANALYSIS RESULTS
            ================================================== */}

            {analysis && (
              <div className="analysis-results">
                {/* ==================================================
                    PROJECT
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <Code2 size={20} />

                    <span>Project</span>
                  </div>

                  <div className="analysis-grid">
                    <div>
                      <span>Framework</span>

                      <strong>{analysis.framework || "Unknown"}</strong>
                    </div>

                    <div>
                      <span>Language</span>

                      <strong>{analysis.language || "Unknown"}</strong>
                    </div>

                    <div>
                      <span>Runtime</span>

                      <strong>{analysis.runtime || "Unknown"}</strong>
                    </div>

                    <div>
                      <span>Package Manager</span>

                      <strong>{analysis.package_manager || "Unknown"}</strong>
                    </div>
                  </div>
                </div>

                {/* ==================================================
                    PORTS
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <Server size={20} />

                    <span>Ports</span>
                  </div>

                  {analysis.ports?.length ? (
                    <div className="dependency-list">
                      {analysis.ports.map((port) => (
                        <div className="dependency-item" key={`port-${port}`}>
                          <span>Application Port</span>

                          <code>{port}</code>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-analysis">No ports detected.</div>
                  )}
                </div>

                {/* ==================================================
                    COMMANDS
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <Terminal size={20} />

                    <span>Commands</span>
                  </div>

                  <div className="command-list">
                    <div>
                      <span>Build</span>

                      <code>{analysis.build_command || "Not detected"}</code>
                    </div>

                    <div>
                      <span>Start</span>

                      <code>{analysis.start_command || "Not detected"}</code>
                    </div>
                  </div>
                </div>

                {/* ==================================================
                    APPLICATIONS
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <Box size={20} />

                    <span>Applications</span>
                  </div>

                  {analysis.applications?.length ? (
                    <div className="application-list">
                      {analysis.applications.map((application, index) => (
                        <div
                          className="application-item"
                          key={`application-${
                            application.path || application.name || index
                          }`}
                        >
                          <div className="application-header">
                            <strong>{application.name || "Application"}</strong>

                            <span>{application.type || "Unknown"}</span>
                          </div>

                          <div className="analysis-grid">
                            <div>
                              <span>Framework</span>

                              <strong>
                                {application.framework || "Unknown"}
                              </strong>
                            </div>

                            <div>
                              <span>Runtime</span>

                              <strong>
                                {application.runtime || "Unknown"}
                              </strong>
                            </div>

                            <div>
                              <span>Port</span>

                              <strong>{application.port || "Unknown"}</strong>
                            </div>

                            <div>
                              <span>Path</span>

                              <strong>{application.path || "."}</strong>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-analysis">
                      No applications detected.
                    </div>
                  )}
                </div>

                {/* ==================================================
                    DEPENDENCIES
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <Package size={20} />

                    <span>Dependencies</span>
                  </div>

                  {analysis.dependencies?.length ? (
                    <div className="dependency-list">
                      {analysis.dependencies.slice(0, 30).map((dependency) => (
                        <div
                          className="dependency-item"
                          key={`dependency-${dependency}`}
                        >
                          <span>{dependency}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-analysis">
                      No package dependencies detected.
                    </div>
                  )}

                  {analysis.dependencies?.length > 30 && (
                    <div className="analysis-note">
                      Showing first 30 of {analysis.dependencies.length}{" "}
                      dependencies.
                    </div>
                  )}
                </div>

                {/* ==================================================
                    PACKAGE FILES
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <Package size={20} />

                    <span>Packages</span>
                  </div>

                  {analysis.packages?.length ? (
                    <div className="application-list">
                      {analysis.packages.map((pkg, index) => (
                        <div
                          className="application-item"
                          key={`package-${pkg.path || index}`}
                        >
                          <div className="application-header">
                            <strong>{pkg.name || "package.json"}</strong>

                            <span>{pkg.path}</span>
                          </div>

                          <div className="analysis-grid">
                            <div>
                              <span>Version</span>

                              <strong>{pkg.version || "Unknown"}</strong>
                            </div>

                            <div>
                              <span>Dependencies</span>

                              <strong>
                                {Object.keys(pkg.dependencies || {}).length}
                              </strong>
                            </div>

                            <div>
                              <span>Scripts</span>

                              <strong>
                                {Object.keys(pkg.scripts || {}).length}
                              </strong>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-analysis">
                      No package files detected.
                    </div>
                  )}
                </div>

                {/* ==================================================
                    FILE STRUCTURE
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <FolderTree size={20} />

                    <span>Project Structure</span>
                  </div>

                  {analysis.structure?.directories?.length ? (
                    <div className="structure-list">
                      {analysis.structure.directories
                        .slice(0, 50)
                        .map((item) => (
                          <div
                            className="structure-item"
                            key={`directory-${item}`}
                          >
                            <FolderTree size={16} />

                            <span>{item}</span>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <div className="empty-analysis">
                      No directories detected.
                    </div>
                  )}
                </div>

                {/* ==================================================
                    ENTRY POINTS
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <FileCode2 size={20} />

                    <span>Entry Points</span>
                  </div>

                  {analysis.entry_points?.length ? (
                    <div className="structure-list">
                      {analysis.entry_points.map((entry) => (
                        <div className="structure-item" key={`entry-${entry}`}>
                          <FileCode2 size={16} />

                          <span>{entry}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-analysis">
                      No entry points detected.
                    </div>
                  )}
                </div>

                {/* ==================================================
                    FILE STATISTICS
                ================================================== */}

                <div className="analysis-card">
                  <div className="analysis-card-title">
                    <Code2 size={20} />

                    <span>Repository Statistics</span>
                  </div>

                  <div className="analysis-grid">
                    <div>
                      <span>Total Files</span>

                      <strong>{analysis.files?.total ?? 0}</strong>
                    </div>

                    <div>
                      <span>Directories</span>

                      <strong>{analysis.files?.directories ?? 0}</strong>
                    </div>

                    <div>
                      <span>Dependencies</span>

                      <strong>{analysis.dependencies?.length ?? 0}</strong>
                    </div>

                    <div>
                      <span>Applications</span>

                      <strong>{analysis.applications?.length ?? 0}</strong>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ==================================================
              PREVIEW
          ================================================== */}

          {sandbox?.preview_url && (
            <div className="preview-section">
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
            </div>
          )}
        </section>

        {/* ==================================================
            FEATURES
        ================================================== */}

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

      {/* ==================================================
          FOOTER
      ================================================== */}

      <footer>
        <span>RepoPilot</span>

        <span className="footer-dot">•</span>

        <span>AI-powered repository demos</span>
      </footer>
    </div>
  );
}

/*
|--------------------------------------------------------------------------
| Feature component
|--------------------------------------------------------------------------
*/

function Feature({ icon, title, description }) {
  return (
    <div className="feature-card">
      <div className="feature-icon">{icon}</div>

      <h3>{title}</h3>

      <p>{description}</p>
    </div>
  );
}

export default Dashboard;
