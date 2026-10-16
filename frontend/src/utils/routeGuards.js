/**
 * ORCA Route Guard & Redirect Logic Utilities
 *
 * Provides pure functions to evaluate navigation redirects and route authorization.
 * Handles all 4 operational states:
 *  1. admin
 *  2. normal-user (researcher, oceanographer, fleet_officer)
 *  3. unauthenticated
 *  4. unknown-role (unassigned, undefined, unknown)
 */

/**
 * Evaluates the root landing destination based on session state and role.
 *
 * @param {Object} authState - { isAuthenticated, isLoading, user }
 * @returns {string|null} Target path or null while loading
 */
export function evaluateRootRedirect({ isAuthenticated, isLoading, user } = {}) {
  if (isLoading) return null;
  if (!isAuthenticated) return '/login';
  return user?.role === 'admin' ? '/admin/dashboard' : '/user/dashboard';
}

/**
 * Evaluates access to a protected route with optional role requirements.
 *
 * @param {Object} params - { isAuthenticated, isLoading, user, requiredRole }
 * @returns {Object} { status: 'loading' | 'redirect_login' | 'restricted' | 'authorized', role?: string }
 */
export function evaluateProtectedRoute({ isAuthenticated, isLoading, user, requiredRole } = {}) {
  if (isLoading) return { status: 'loading' };
  if (!isAuthenticated) return { status: 'redirect_login' };
  if (requiredRole && user?.role !== requiredRole) {
    return { status: 'restricted', role: user?.role || 'unassigned' };
  }
  return { status: 'authorized' };
}
