import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { evaluateRootRedirect, evaluateProtectedRoute } from '../src/utils/routeGuards.js';

describe('RootRedirect & ProtectedRoute Authorization Matrix Tests', () => {
  describe('RootRedirect (Landing Navigation)', () => {
    it('1. Returns null while authentication state is loading', () => {
      const result = evaluateRootRedirect({ isLoading: true, isAuthenticated: false, user: null });
      assert.equal(result, null);
    });

    it('2. Unauthenticated user redirects to /login', () => {
      const result = evaluateRootRedirect({ isLoading: false, isAuthenticated: false, user: null });
      assert.equal(result, '/login');
    });

    it('3. Authenticated Admin redirects directly to /admin/dashboard', () => {
      const adminUser = { id: 'adm_1', fullName: 'Chief Administrator', role: 'admin' };
      const result = evaluateRootRedirect({ isLoading: false, isAuthenticated: true, user: adminUser });
      assert.equal(result, '/admin/dashboard');
    });

    it('4. Authenticated Normal User (researcher) redirects to /user/dashboard', () => {
      const normalUser = { id: 'usr_1', fullName: 'Dr. Marine Scientist', role: 'researcher' };
      const result = evaluateRootRedirect({ isLoading: false, isAuthenticated: true, user: normalUser });
      assert.equal(result, '/user/dashboard');
    });

    it('5. Authenticated Normal User (oceanographer / fleet_officer) redirects to /user/dashboard', () => {
      const oceanographer = { id: 'usr_2', fullName: 'Ocean Analyst', role: 'oceanographer' };
      assert.equal(
        evaluateRootRedirect({ isLoading: false, isAuthenticated: true, user: oceanographer }),
        '/user/dashboard'
      );

      const fleetOfficer = { id: 'usr_3', fullName: 'Fleet Commander', role: 'fleet_officer' };
      assert.equal(
        evaluateRootRedirect({ isLoading: false, isAuthenticated: true, user: fleetOfficer }),
        '/user/dashboard'
      );
    });

    it('6. Unknown-role user safely defaults to /user/dashboard without elevated privileges', () => {
      const unknownRoleUser = { id: 'usr_4', fullName: 'Guest User', role: 'unknown_role' };
      assert.equal(
        evaluateRootRedirect({ isLoading: false, isAuthenticated: true, user: unknownRoleUser }),
        '/user/dashboard'
      );

      const nullRoleUser = { id: 'usr_5', fullName: 'Unassigned User', role: null };
      assert.equal(
        evaluateRootRedirect({ isLoading: false, isAuthenticated: true, user: nullRoleUser }),
        '/user/dashboard'
      );

      const undefinedRoleUser = { id: 'usr_6', fullName: 'Missing Role User' };
      assert.equal(
        evaluateRootRedirect({ isLoading: false, isAuthenticated: true, user: undefinedRoleUser }),
        '/user/dashboard'
      );
    });
  });

  describe('ProtectedRoute (Route-Level Guard & RBAC)', () => {
    it('1. Returns loading status while session initializes', () => {
      const decision = evaluateProtectedRoute({
        isLoading: true,
        isAuthenticated: false,
        user: null,
        requiredRole: 'admin',
      });
      assert.deepEqual(decision, { status: 'loading' });
    });

    it('2. Unauthenticated user attempting to access protected route triggers redirect to /login', () => {
      const decisionAdminRoute = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        requiredRole: 'admin',
      });
      assert.deepEqual(decisionAdminRoute, { status: 'redirect_login' });

      const decisionUserRoute = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        requiredRole: undefined,
      });
      assert.deepEqual(decisionUserRoute, { status: 'redirect_login' });
    });

    it('3. Authenticated Admin accessing requiredRole="admin" is authorized', () => {
      const adminUser = { id: 'adm_1', fullName: 'Admin User', role: 'admin' };
      const decision = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: true,
        user: adminUser,
        requiredRole: 'admin',
      });
      assert.deepEqual(decision, { status: 'authorized' });
    });

    it('4. Authenticated Normal User accessing requiredRole="admin" is restricted', () => {
      const researcher = { id: 'usr_1', fullName: 'Researcher User', role: 'researcher' };
      const decision = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: true,
        user: researcher,
        requiredRole: 'admin',
      });
      assert.deepEqual(decision, { status: 'restricted', role: 'researcher' });
    });

    it('5. Unknown-role user accessing requiredRole="admin" is restricted', () => {
      const unknownUser = { id: 'usr_9', fullName: 'Unknown Role', role: 'unknown_role' };
      const decision = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: true,
        user: unknownUser,
        requiredRole: 'admin',
      });
      assert.deepEqual(decision, { status: 'restricted', role: 'unknown_role' });

      const nullRoleUser = { id: 'usr_10', fullName: 'Null Role User', role: null };
      const decisionNull = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: true,
        user: nullRoleUser,
        requiredRole: 'admin',
      });
      assert.deepEqual(decisionNull, { status: 'restricted', role: 'unassigned' });
    });

    it('6. Normal User accessing standard user workspace (no requiredRole) is authorized', () => {
      const researcher = { id: 'usr_1', fullName: 'Researcher User', role: 'researcher' };
      const decision = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: true,
        user: researcher,
        requiredRole: undefined,
      });
      assert.deepEqual(decision, { status: 'authorized' });
    });

    it('7. Admin accessing standard user workspace (no requiredRole) is also authorized', () => {
      const adminUser = { id: 'adm_1', fullName: 'Admin User', role: 'admin' };
      const decision = evaluateProtectedRoute({
        isLoading: false,
        isAuthenticated: true,
        user: adminUser,
        requiredRole: undefined,
      });
      assert.deepEqual(decision, { status: 'authorized' });
    });
  });
});
