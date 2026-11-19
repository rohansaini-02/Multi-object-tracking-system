import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  Activity,
  Cpu,
  Terminal,
  CheckCircle2,
} from 'lucide-react';
import { loginApi, registerApi, loginWithGoogleApi, getCurrentUserApi } from '../api/client';

const GOOGLE_CLIENT_ID = '747165820254-cqro19d06pdiaad112j95djupapt51oh.apps.googleusercontent.com';

export default function Login({ setActivePage, onAuthenticated, notice }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isGoogleHovered, setIsGoogleHovered] = useState(false);
  const [error, setError] = useState(notice || '');
  const [successMessage, setSuccessMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const googleBtnContainerRef = useRef(null);
  const isRegister = mode === 'register';

  // Calculate password strength for registration
  const passwordScore = useMemo(() => {
    if (!password) return 0;
    let score = 0;
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
    if (/[0-9]/.test(password) || /[^A-Za-z0-9]/.test(password)) score += 1;
    return score;
  }, [password]);

  const strengthMeta = useMemo(() => {
    switch (passwordScore) {
      case 1:
        return { label: 'Weak', color: 'var(--accent-rose)', width: '25%' };
      case 2:
        return { label: 'Fair', color: 'var(--accent-amber)', width: '50%' };
      case 3:
        return { label: 'Good', color: 'var(--accent-cyan)', width: '75%' };
      case 4:
        return { label: 'Strong', color: 'var(--accent-emerald)', width: '100%' };
      default:
        return { label: '', color: 'transparent', width: '0%' };
    }
  }, [passwordScore]);

  const handleGoogleSuccess = useCallback(async (response) => {
    setError('');
    setSuccessMessage('');
    setIsSubmitting(true);
    try {
      await loginWithGoogleApi(response.credential);
      const user = await getCurrentUserApi();
      setIsSubmitting(false);
      if (onAuthenticated) onAuthenticated(user);
      else if (setActivePage) setActivePage('dashboard');
    } catch (err) {
      setIsSubmitting(false);
      setError(err.message || 'Google authentication failed. Please try again.');
    }
  }, [onAuthenticated, setActivePage]);

  // Initialize and mount Google Identity Services
  useEffect(() => {
    let timer = null;

    const renderGoogleBtn = () => {
      if (window.google?.accounts?.id && googleBtnContainerRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: handleGoogleSuccess,
            auto_select: false,
          });

          googleBtnContainerRef.current.innerHTML = '';
          window.google.accounts.id.renderButton(googleBtnContainerRef.current, {
            theme: 'filled_black',
            size: 'large',
            shape: 'rectangular',
            text: isRegister ? 'signup_with' : 'signin_with',
            width: 360,
          });
        } catch (err) {
          console.warn('Google Identity initialization error:', err);
        }
      } else {
        timer = setTimeout(renderGoogleBtn, 250);
      }
    };

    if (!document.getElementById('google-gsi-script')) {
      const script = document.createElement('script');
      script.id = 'google-gsi-script';
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = renderGoogleBtn;
      document.body.appendChild(script);
    } else {
      renderGoogleBtn();
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [isRegister, handleGoogleSuccess]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setIsSubmitting(true);

    try {
      if (isRegister) {
        if (password !== confirmPassword) {
          setIsSubmitting(false);
          setError('Passwords do not match. Please verify both password entries.');
          return;
        }
        // Create new account
        await registerApi(email, password, name);
        setIsSubmitting(false);
        setPassword('');
        setConfirmPassword('');
        setMode('login'); // Switch user to Sign In view
        setSuccessMessage('Account created successfully! Please enter your password to sign in.');
        return;
      }

      // Sign In mode
      await loginApi(email, password);
      const user = await getCurrentUserApi();

      setIsSubmitting(false);
      if (onAuthenticated) onAuthenticated(user || { email });
      else if (setActivePage) setActivePage('dashboard');
    } catch (err) {
      setIsSubmitting(false);
      setError(err.message || 'Authentication failed. Please verify credentials.');
    }
  };

  return (
    <div
      style={{
        minHeight: 'calc(100vh - 120px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px 10px',
      }}
    >
      <div
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '1020px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
          borderRadius: '16px',
          border: '1px solid var(--border-strong)',
          overflow: 'hidden',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.8), 0 0 1px 1px rgba(0, 229, 255, 0.15)',
          background: 'linear-gradient(145deg, #050508 0%, #000000 100%)',
        }}
      >
        {/* ================================================================= */}
        {/* LEFT PANEL: Telemetry Showcase & Mission Control HUD             */}
        {/* ================================================================= */}
        <div
          style={{
            padding: '48px 40px',
            borderRight: '1px solid var(--border-subtle)',
            background: 'radial-gradient(circle at 10% 20%, rgba(0, 229, 255, 0.05) 0%, transparent 60%)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            position: 'relative',
          }}
        >
          {/* Subtle Cyber Grid Background Overlay */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              opacity: 0.04,
              backgroundImage:
                'linear-gradient(to right, #00E5FF 1px, transparent 1px), linear-gradient(to bottom, #00E5FF 1px, transparent 1px)',
              backgroundSize: '24px 24px',
              pointerEvents: 'none',
            }}
          />

          <div>
            {/* Top Operational Pill */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 10px',
                  borderRadius: '20px',
                  backgroundColor: 'rgba(0, 229, 255, 0.08)',
                  border: '1px solid rgba(0, 229, 255, 0.3)',
                  fontSize: '0.7rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--accent-cyan)',
                  letterSpacing: '0.08em',
                  fontWeight: 600,
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent-cyan)',
                    boxShadow: '0 0 8px var(--accent-cyan)',
                  }}
                />
                TACTICAL VISION OS • ONLINE
              </span>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                }}
              >
                v0.1.0-RC
              </span>
            </div>

            {/* Heading & Platform Description */}
            <h1
              style={{
                fontSize: '2rem',
                fontWeight: 800,
                lineHeight: 1.15,
                color: 'var(--text-primary)',
                letterSpacing: '-0.03em',
                marginBottom: '12px',
              }}
            >
              Enterprise Multi-Object{' '}
              <span
                style={{
                  background: 'linear-gradient(90deg, #00E5FF, #3b82f6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Detection &amp; Tracking
              </span>
            </h1>
            <p
              style={{
                fontSize: '0.88rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
                marginBottom: '32px',
              }}
            >
              Real-time deep association tracking powered by YOLOv8, DeepSORT, 8-state Kalman filtering, and OSNet Re-ID neural embeddings.
            </p>

            {/* Interactive Simulated Vision Target HUD Display */}
            <div
              style={{
                borderRadius: '12px',
                border: '1px solid var(--border-strong)',
                backgroundColor: 'rgba(6, 6, 10, 0.75)',
                padding: '20px',
                position: 'relative',
                overflow: 'hidden',
                marginBottom: '32px',
                backdropFilter: 'blur(8px)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '16px',
                  borderBottom: '1px solid var(--border-subtle)',
                  paddingBottom: '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Terminal size={14} color="var(--accent-cyan)" />
                  <span
                    className="font-mono"
                    style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', fontWeight: 600 }}
                  >
                    LIVE_INFERENCE_PIPELINE
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span
                    className="font-mono"
                    style={{
                      fontSize: '0.65rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: 'rgba(16, 185, 129, 0.15)',
                      color: 'var(--accent-emerald)',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                    }}
                  >
                    60.2 FPS
                  </span>
                  <span
                    className="font-mono"
                    style={{
                      fontSize: '0.65rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: 'rgba(0, 229, 255, 0.1)',
                      color: 'var(--accent-cyan)',
                      border: '1px solid rgba(0, 229, 255, 0.25)',
                    }}
                  >
                    3.8ms
                  </span>
                </div>
              </div>

              {/* Simulated Detection Track Bounding Boxes */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(0, 229, 255, 0.05)',
                    borderLeft: '3px solid var(--accent-cyan)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      className="font-mono"
                      style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 600 }}
                    >
                      #TRACK-042
                    </span>
                    <span
                      style={{
                        fontSize: '0.68rem',
                        color: 'var(--accent-cyan)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      PERSON [0.984]
                    </span>
                  </div>
                  <span
                    className="font-mono"
                    style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}
                  >
                    XYWH:[210, 184, 94, 218]
                  </span>
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    borderLeft: '3px solid var(--accent-emerald)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      className="font-mono"
                      style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 600 }}
                    >
                      #TRACK-108
                    </span>
                    <span
                      style={{
                        fontSize: '0.68rem',
                        color: 'var(--accent-emerald)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      VEHICLE [0.962]
                    </span>
                  </div>
                  <span
                    className="font-mono"
                    style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}
                  >
                    XYWH:[540, 312, 182, 140]
                  </span>
                </div>
              </div>
            </div>

            {/* Feature Highlights List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(0, 229, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: '2px',
                  }}
                >
                  <Cpu size={15} color="var(--accent-cyan)" />
                </div>
                <div>
                  <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    DeepSORT Tracking Architecture
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '1px' }}>
                    Cascaded matching associating YOLOv8 detections with deep OSNet Re-ID embeddings and spatial Kalman motion predictions.
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: '2px',
                  }}
                >
                  <Activity size={15} color="var(--accent-emerald)" />
                </div>
                <div>
                  <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Standardized MOT17 Benchmark Suite
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '1px' }}>
                    One-click validation compute for HOTA, MOTA, IDF1, and Identity Switch telemetry.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Security Badge */}
          <div
            style={{
              paddingTop: '24px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginTop: '32px',
            }}
          >
            <ShieldCheck size={16} color="var(--accent-emerald)" />
            <span
              className="font-mono"
              style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}
            >
              Hardware-Accelerated Ingest • 256-Bit Encrypted Session
            </span>
          </div>
        </div>

        {/* ================================================================= */}
        {/* RIGHT PANEL: Authentication Form & Google OAuth                   */}
        {/* ================================================================= */}
        <div
          style={{
            padding: '48px 42px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
          }}
        >
          {/* Mode Switcher Tabs */}
          <div
            style={{
              display: 'flex',
              padding: '4px',
              backgroundColor: 'var(--bg-elevated)',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
              marginBottom: '28px',
            }}
          >
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setError('');
                setSuccessMessage('');
              }}
              style={{
                flex: 1,
                padding: '9px 16px',
                borderRadius: '6px',
                border: 'none',
                background: !isRegister ? 'rgba(0, 229, 255, 0.15)' : 'transparent',
                color: !isRegister ? 'var(--accent-cyan)' : 'var(--text-muted)',
                fontWeight: !isRegister ? 700 : 500,
                fontSize: '0.82rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('register');
                setError('');
                setSuccessMessage('');
              }}
              style={{
                flex: 1,
                padding: '9px 16px',
                borderRadius: '6px',
                border: 'none',
                background: isRegister ? 'rgba(0, 229, 255, 0.15)' : 'transparent',
                color: isRegister ? 'var(--accent-cyan)' : 'var(--text-muted)',
                fontWeight: isRegister ? 700 : 500,
                fontSize: '0.82rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              Create Account
            </button>
          </div>

          {/* Form Header */}
          <div style={{ marginBottom: '22px' }}>
            <h2
              style={{
                fontSize: '1.5rem',
                fontWeight: 800,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
              }}
            >
              {isRegister ? 'Create Your Account' : 'Welcome Back'}
            </h2>
            <p
              style={{
                color: 'var(--text-secondary)',
                fontSize: '0.82rem',
                marginTop: '6px',
                lineHeight: 1.5,
              }}
            >
              {isRegister
                ? 'Register your telemetry identity to ingest video datasets and execute tracking models.'
                : 'Sign in to access your models, active tracking jobs, and benchmark telemetry.'}
            </p>
          </div>

          {/* Success Notice Banner */}
          {successMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 14px',
                borderRadius: '8px',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                color: 'var(--accent-emerald)',
                fontSize: '0.8rem',
                marginBottom: '20px',
              }}
            >
              <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
              <div style={{ flex: 1, lineHeight: 1.4 }}>{successMessage}</div>
            </div>
          )}

          {/* Error Notice Banner */}
          {error && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 14px',
                borderRadius: '8px',
                backgroundColor: 'rgba(244, 63, 94, 0.12)',
                border: '1px solid rgba(244, 63, 94, 0.35)',
                color: 'var(--accent-rose)',
                fontSize: '0.8rem',
                marginBottom: '20px',
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <div style={{ flex: 1, lineHeight: 1.4 }}>{error}</div>
            </div>
          )}

          {/* Main Credentials Form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {isRegister && (
              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                    letterSpacing: '0.04em',
                  }}
                >
                  FULL NAME
                </label>
                <div style={{ position: 'relative' }}>
                  <User
                    size={16}
                    color="var(--text-muted)"
                    style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }}
                  />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Dr. Alex Mercer"
                    style={{
                      width: '100%',
                      padding: '12px 14px 12px 40px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--bg-elevated)',
                      border: '1px solid var(--border-strong)',
                      color: 'var(--text-primary)',
                      outline: 'none',
                      fontSize: '0.85rem',
                      transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = 'var(--accent-cyan)';
                      e.target.style.boxShadow = '0 0 0 2px rgba(0, 229, 255, 0.15)';
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = 'var(--border-strong)';
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                </div>
              </div>
            )}

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                  letterSpacing: '0.04em',
                }}
              >
                EMAIL ADDRESS
              </label>
              <div style={{ position: 'relative' }}>
                <Mail
                  size={16}
                  color="var(--text-muted)"
                  style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }}
                />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@visionops.io"
                  required
                  style={{
                    width: '100%',
                    padding: '12px 14px 12px 40px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border-strong)',
                    color: 'var(--text-primary)',
                    outline: 'none',
                    fontSize: '0.85rem',
                    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--accent-cyan)';
                    e.target.style.boxShadow = '0 0 0 2px rgba(0, 229, 255, 0.15)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--border-strong)';
                    e.target.style.boxShadow = 'none';
                  }}
                />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label
                  style={{
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.04em',
                  }}
                >
                  PASSWORD
                </label>
                {isRegister && strengthMeta.label && (
                  <span
                    className="font-mono"
                    style={{ fontSize: '0.7rem', color: strengthMeta.color, fontWeight: 600 }}
                  >
                    Strength: {strengthMeta.label}
                  </span>
                )}
              </div>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={16}
                  color="var(--text-muted)"
                  style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }}
                />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  minLength={8}
                  style={{
                    width: '100%',
                    padding: '12px 85px 12px 40px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border-strong)',
                    color: 'var(--text-primary)',
                    outline: 'none',
                    fontSize: '0.85rem',
                    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--accent-cyan)';
                    e.target.style.boxShadow = '0 0 0 2px rgba(0, 229, 255, 0.15)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--border-strong)';
                    e.target.style.boxShadow = 'none';
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: showPassword ? 'rgba(0, 229, 255, 0.12)' : 'rgba(255, 255, 255, 0.05)',
                    border: showPassword ? '1px solid rgba(0, 229, 255, 0.4)' : '1px solid var(--border-subtle)',
                    color: showPassword ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    padding: '5px 8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 600,
                    transition: 'all 0.2s ease',
                  }}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  <span>{showPassword ? 'Hide' : 'Show'}</span>
                </button>
              </div>

              {/* Password Strength Visual Meter */}
              {isRegister && password && (
                <div style={{ marginTop: '8px' }}>
                  <div
                    style={{
                      height: '4px',
                      backgroundColor: 'var(--border-strong)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: strengthMeta.width,
                        backgroundColor: strengthMeta.color,
                        transition: 'width 0.3s ease, background-color 0.3s ease',
                      }}
                    />
                  </div>
                  <div
                    style={{
                      fontSize: '0.68rem',
                      color: 'var(--text-muted)',
                      marginTop: '5px',
                    }}
                  >
                    Must be at least 8 characters with letters and numbers
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password Field (Register Mode) */}
            {isRegister && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label
                    style={{
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      color: 'var(--text-secondary)',
                      letterSpacing: '0.04em',
                    }}
                  >
                    CONFIRM PASSWORD
                  </label>
                  {confirmPassword && (
                    <span
                      className="font-mono"
                      style={{
                        fontSize: '0.7rem',
                        color: password === confirmPassword ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                        fontWeight: 600,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      {password === confirmPassword ? (
                        <>
                          <CheckCircle2 size={12} /> Passwords Match
                        </>
                      ) : (
                        <>
                          <AlertCircle size={12} /> Passwords Do Not Match
                        </>
                      )}
                    </span>
                  )}
                </div>
                <div style={{ position: 'relative' }}>
                  <Lock
                    size={16}
                    color="var(--text-muted)"
                    style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }}
                  />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    minLength={8}
                    style={{
                      width: '100%',
                      padding: '12px 85px 12px 40px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--bg-elevated)',
                      border: '1px solid var(--border-strong)',
                      color: 'var(--text-primary)',
                      outline: 'none',
                      fontSize: '0.85rem',
                      transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = 'var(--accent-cyan)';
                      e.target.style.boxShadow = '0 0 0 2px rgba(0, 229, 255, 0.15)';
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = 'var(--border-strong)';
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: showConfirmPassword ? 'rgba(0, 229, 255, 0.12)' : 'rgba(255, 255, 255, 0.05)',
                      border: showConfirmPassword ? '1px solid rgba(0, 229, 255, 0.4)' : '1px solid var(--border-subtle)',
                      color: showConfirmPassword ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      padding: '5px 8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      fontSize: '0.72rem',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      transition: 'all 0.2s ease',
                    }}
                    title={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  >
                    {showConfirmPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    <span>{showConfirmPassword ? 'Hide' : 'Show'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Submit Action Button */}
            <button
              type="submit"
              className="btn btn-cyan"
              disabled={isSubmitting}
              style={{
                marginTop: '10px',
                padding: '13px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '0.88rem',
                letterSpacing: '0.02em',
                fontWeight: 700,
              }}
            >
              {isSubmitting ? (
                <>
                  <span
                    style={{
                      width: '16px',
                      height: '16px',
                      border: '2px solid rgba(4, 13, 20, 0.4)',
                      borderTopColor: '#040D14',
                      borderRadius: '50%',
                      animation: 'spin 0.8s linear infinite',
                    }}
                  />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>{isRegister ? 'Create Account' : 'Authenticate Session'}</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Tactical Divider */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              margin: '24px 0 20px 0',
            }}
          >
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle)' }} />
            <span
              className="font-mono"
              style={{
                fontSize: '0.66rem',
                color: 'var(--text-muted)',
                letterSpacing: '0.08em',
              }}
            >
              OR CONTINUE WITH GOOGLE
            </span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle)' }} />
          </div>

          {/* Custom Cyber Google OAuth Button with Invisible Native GIS Overlay */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '46px',
              borderRadius: '8px',
              overflow: 'hidden',
              backgroundColor: 'var(--bg-elevated)',
              border: isGoogleHovered ? '1px solid var(--accent-cyan)' : '1px solid var(--border-strong)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              cursor: 'pointer',
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              boxShadow: isGoogleHovered ? '0 0 20px rgba(0, 229, 255, 0.22)' : 'none',
              transform: isGoogleHovered ? 'translateY(-1px)' : 'none',
            }}
            onMouseEnter={() => setIsGoogleHovered(true)}
            onMouseLeave={() => setIsGoogleHovered(false)}
          >
            {/* Crisp Official Multi-Color Google G Logo SVG */}
            <svg width="20" height="20" viewBox="0 0 24 24" style={{ flexShrink: 0, pointerEvents: 'none' }}>
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>

            {/* Typography matching platform buttons */}
            <span
              style={{
                fontSize: '0.86rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                letterSpacing: '0.01em',
                pointerEvents: 'none',
              }}
            >
              {isRegister ? 'Sign up with Google' : 'Sign in with Google'}
            </span>

            {/* Native Google Identity Services Button Transparent Overlay */}
            <div
              ref={googleBtnContainerRef}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                opacity: 0.001,
                overflow: 'hidden',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                zIndex: 2,
              }}
            />
          </div>

          {/* Quick Switch Switcher */}
          <div
            style={{
              textAlign: 'center',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              marginTop: '24px',
            }}
          >
            {isRegister ? 'Already have an existing account?' : "Don't have an operator account yet?"}{' '}
            <button
              type="button"
              onClick={() => {
                setMode(isRegister ? 'login' : 'register');
                setError('');
                setSuccessMessage('');
              }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-cyan)',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 600,
                padding: 0,
                textDecoration: 'underline',
                textUnderlineOffset: '3px',
              }}
            >
              {isRegister ? 'Sign In here' : 'Register here'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
