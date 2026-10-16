import React from 'react';
import { Link } from 'react-router-dom';
import OrcaLogo from '../components/OrcaLogo';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
      <OrcaLogo variant="large" className="mb-4" />

      <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
        Sector Not Found (404)
      </h1>
      <p className="mt-2 text-sm text-slate-500 max-w-sm mx-auto leading-relaxed">
        The coordinates or oceanographic view you requested does not exist in the ORCA routing network.
      </p>

      <div className="mt-6 flex gap-3">
        <Link
          to="/user/dashboard"
          className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs transition-colors shadow-xs"
        >
          Return to Chat Workspace
        </Link>
        <Link
          to="/login"
          className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-200 transition-colors"
        >
          Go to Sign In
        </Link>
      </div>
    </div>
  );
}
