import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, Rocket, UserPlus, XCircle } from "lucide-react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Signup() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
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
      const response = await axios.post(`${API_URL}/api/auth/signup`, form);

      const { access_token, user } = response.data;

      localStorage.setItem("repopilot_token", access_token);

      localStorage.setItem("repopilot_user", JSON.stringify(user));

      navigate("/");
    } catch (err) {
      const message =
        err?.response?.data?.detail || "Unable to create your account.";

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
          <h1>Create your account</h1>

          <p>Start turning GitHub repositories into live demos.</p>
        </div>

        {error && (
          <div className="auth-error">
            <XCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="name">Name</label>

            <input
              id="name"
              name="name"
              type="text"
              placeholder="Ninaad"
              value={form.name}
              onChange={handleChange}
              autoComplete="name"
              required
            />
          </div>

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
              placeholder="Minimum 8 characters"
              value={form.password}
              onChange={handleChange}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={18} className="spin" />
                Creating account...
              </>
            ) : (
              <>
                <UserPlus size={18} />
                Create account
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          <span>Already have an account?</span>

          <Link to="/login">Log in</Link>
        </div>
      </div>
    </div>
  );
}

export default Signup;
