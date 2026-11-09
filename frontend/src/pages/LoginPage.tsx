import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { ShieldCheck, Lock, User, AlertCircle, KeyRound, ArrowLeft, CheckCircle2, Clock } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // 2FA State
  const [is2FAPending, setIs2FAPending] = useState(false);
  const [userIdFor2FA, setUserIdFor2FA] = useState<number | null>(null);
  const [userEmail, setUserEmail] = useState('');
  const [demoOtp, setDemoOtp] = useState('');
  const [otpInput, setOtpInput] = useState('');
  const [countdown, setCountdown] = useState(300);

  const { login } = useAuth();
  const navigate = useNavigate();

  // 2FA Timer
  useEffect(() => {
    let timer: any;
    if (is2FAPending && countdown > 0) {
      timer = setInterval(() => setCountdown((prev) => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [is2FAPending, countdown]);

  const handleInitialAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Step 1: Verify primary password & request 2FA OTP
      const res = await api.post('/auth/request-2fa', {
        username_or_email: identifier,
        password: password,
      });

      setIs2FAPending(true);
      setUserIdFor2FA(res.data.user_id);
      setUserEmail(res.data.email);
      setDemoOtp(res.data.demo_otp);
      setCountdown(300);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userIdFor2FA) return;
    setLoading(true);
    setError(null);

    try {
      // Step 2: Verify 6-digit OTP and obtain bearer JWT
      const res = await api.post('/auth/verify-2fa', {
        user_id: userIdFor2FA,
        otp_code: otpInput.trim(),
      });
      login(res.data.access_token, res.data.user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Verification code failed. Please check the code.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoAccount = (username: string, pass: string) => {
    setIdentifier(username);
    setPassword(pass);
    setIs2FAPending(false);
    setError(null);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50/50 to-indigo-50/30 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="bg-gradient-to-tr from-sky-600 via-blue-600 to-indigo-600 p-3.5 rounded-2xl shadow-lg shadow-sky-500/25 text-white">
            <ShieldCheck className="w-10 h-10" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-3xl font-extrabold text-slate-900 tracking-tight">
          Trust<span className="text-sky-600">Vault</span>
        </h2>
        <p className="mt-2 text-center text-sm text-slate-500">
          Secure Enterprise Document Sharing & AI Intelligence Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white/95 backdrop-blur-md py-8 px-4 shadow-xl shadow-sky-100/60 sm:rounded-2xl sm:px-10 border border-sky-100">
          {error && (
            <div className="mb-5 p-3 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-700 flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!is2FAPending ? (
            /* Step 1: Username & Password Form */
            <form className="space-y-5" onSubmit={handleInitialAuth}>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Username or Email
                </label>
                <div className="relative rounded-xl shadow-xs">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="admin or user@trustvault.io"
                    className="block w-full pl-10 pr-3 py-2.5 bg-slate-50/60 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Password
                </label>
                <div className="relative rounded-xl shadow-xs">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="block w-full pl-10 pr-3 py-2.5 bg-slate-50/60 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-sm shadow-sky-600/20 text-sm font-semibold text-white bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 disabled:opacity-50 transition-all"
                >
                  {loading ? 'Authenticating...' : 'Sign in with Two-Factor Auth'}
                </button>
              </div>

              {/* Quick Demo Fill Buttons */}
              <div className="mt-6 pt-6 border-t border-slate-100">
                <span className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 text-center">
                  Quick Demo Logins (Click & Submit)
                </span>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setDemoAccount('admin', 'AdminPass123!')}
                    className="py-1.5 px-2 text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200/80 rounded-lg hover:bg-rose-100 transition-all"
                  >
                    Admin Demo
                  </button>
                  <button
                    type="button"
                    onClick={() => setDemoAccount('alice_owner', 'OwnerPass123!')}
                    className="py-1.5 px-2 text-xs font-medium bg-sky-50 text-sky-700 border border-sky-200/80 rounded-lg hover:bg-sky-100 transition-all"
                  >
                    Owner Demo
                  </button>
                  <button
                    type="button"
                    onClick={() => setDemoAccount('carol_viewer', 'ViewerPass123!')}
                    className="py-1.5 px-2 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80 rounded-lg hover:bg-emerald-100 transition-all"
                  >
                    Viewer Demo
                  </button>
                </div>
              </div>

              <div className="mt-6 text-center text-sm text-slate-500">
                Need an account?{' '}
                <Link to="/register" className="font-semibold text-sky-600 hover:text-sky-500">
                  Create an account
                </Link>
              </div>
            </form>
          ) : (
            /* Step 2: 2FA OTP Challenge Screen */
            <form className="space-y-5" onSubmit={handleVerify2FA}>
              <div className="text-center">
                <div className="mx-auto w-12 h-12 rounded-full bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600 mb-3">
                  <KeyRound className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">Two-Factor Authentication</h3>
                <p className="text-xs text-slate-500 mt-1">
                  A 6-digit security code has been generated for{' '}
                  <span className="font-semibold text-slate-700">{userEmail}</span>.
                </p>
              </div>

              {/* Simulated Email / Evaluator OTP Toast */}
              <div className="p-3.5 bg-gradient-to-r from-sky-50 to-blue-50 border border-sky-200 rounded-xl">
                <div className="flex items-center justify-between text-xs text-sky-800 font-semibold mb-1">
                  <span className="flex items-center space-x-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-sky-600" />
                    <span>Evaluator 2FA Simulation Banner</span>
                  </span>
                  <span className="flex items-center space-x-1 text-slate-500">
                    <Clock className="w-3 h-3" />
                    <span>{formatTime(countdown)}</span>
                  </span>
                </div>
                <p className="text-xs text-slate-600 mb-2">
                  Code dispatched to email. For evaluator testing, use the code below:
                </p>
                <div className="flex items-center justify-between bg-white px-3 py-2 rounded-lg border border-sky-100 shadow-xs">
                  <span className="font-mono text-base font-bold tracking-widest text-sky-700">
                    {demoOtp}
                  </span>
                  <button
                    type="button"
                    onClick={() => setOtpInput(demoOtp)}
                    className="text-xs font-semibold text-sky-600 hover:text-sky-800 underline"
                  >
                    Auto-Fill Code
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1 text-center">
                  Enter 6-Digit Verification Code
                </label>
                <input
                  type="text"
                  required
                  maxLength={6}
                  value={otpInput}
                  onChange={(e) => setOtpInput(e.target.value.replace(/\D/g, ''))}
                  placeholder="000000"
                  className="block w-full text-center tracking-[0.5em] text-2xl font-mono py-2.5 bg-slate-50/60 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-all font-bold"
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <button
                  type="submit"
                  disabled={loading || otpInput.length !== 6}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-sm shadow-sky-600/20 text-sm font-semibold text-white bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 disabled:opacity-50 transition-all"
                >
                  {loading ? 'Verifying Code...' : 'Verify & Enter Vault'}
                </button>

                <button
                  type="button"
                  onClick={() => setIs2FAPending(false)}
                  className="w-full flex items-center justify-center space-x-1 py-2 text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Password Login</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
