import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, LogIn, Rocket, XCircle } from "lucide-react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, form);

      const { access_token, user } = response.data;

      localStorage.setItem("repopilot_token", access_token);
      localStorage.setItem("repopilot_user", JSON.stringify(user));

      axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;

      navigate("/");
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        "Unable to login. Please check your credentials.";

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="background-glow glow-one" />
      <div className="background-glow glow-two" />

      <div className="auth-card">
        <div className="auth-brand">
          <div className="brand-icon">
            <Rocket size={20} />
          </div>

          <span>RepoPilot</span>
        </div>

        <div className="auth-header">
          <h1>Welcome back</h1>

          <p>Sign in to continue to your RepoPilot workspace.</p>
        </div>

        {error && (
          <div className="auth-error">
            <XCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="email">Email</label>

            <input
              id="email"
              name="email"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">Password</label>

            <input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={handleChange}
              autoComplete="current-password"
              required
            />
          </div>

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={18} className="spin" />
                Signing in...
              </>
            ) : (
              <>
                <LogIn size={18} />
                Sign in
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          <span>Don't have an account?</span>

          <Link to="/signup">Create one</Link>
        </div>
      </div>
    </div>
  );
}

export default Login;
