import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  validateFullName,
  validateEmail,
  validatePassword,
  validateConfirmPassword,
  validateLoginPassword,
  checkPasswordRequirements,
  REGEX_FULL_NAME,
  REGEX_EMAIL,
  REGEX_PASSWORD,
} from '../src/utils/validation.js';

describe('ORCA Frontend Authentication — Unit & Regex Tests', () => {
  describe('1. Full Name Validation', () => {
    it('rejects empty or whitespace-only names', () => {
      assert.equal(validateFullName(''), 'Full Name is required.');
      assert.equal(validateFullName('   '), 'Full Name is required.');
      assert.equal(validateFullName(null), 'Full Name is required.');
      assert.equal(validateFullName(undefined), 'Full Name is required.');
    });

    it('rejects single character names (< 2 chars)', () => {
      assert.equal(validateFullName('A'), 'Full Name must be at least 2 characters long.');
    });

    it('accepts valid scientific researcher names (letters, spaces, apostrophes, hyphens, periods)', () => {
      assert.equal(validateFullName('Rachel Carson'), '');
      assert.equal(validateFullName('Dr. Sylvia Earle'), '');
      assert.equal(validateFullName('Jacques-Yves Cousteau'), '');
      assert.equal(validateFullName("Liam O'Connor"), '');
      assert.equal(validateFullName('Jean-Luc Picard'), '');
      assert.ok(REGEX_FULL_NAME.test('Dr. Rachel Carson'));
    });

    it('rejects names with numbers or illegal symbols', () => {
      assert.equal(
        validateFullName('Rachel123'),
        'Full Name can only contain letters, spaces, apostrophes, or hyphens.'
      );
      assert.equal(
        validateFullName('Dr. Marine <Script>'),
        'Full Name can only contain letters, spaces, apostrophes, or hyphens.'
      );
      assert.equal(
        validateFullName('Ocean_User!'),
        'Full Name can only contain letters, spaces, apostrophes, or hyphens.'
      );
    });
  });

  describe('2. Email Regex Validation', () => {
    it('rejects empty emails', () => {
      assert.equal(validateEmail(''), 'Email address is required.');
      assert.equal(validateEmail('   '), 'Email address is required.');
    });

    it('rejects malformed email formats', () => {
      assert.equal(
        validateEmail('not-an-email'),
        'Please enter a valid scientific email address (e.g. researcher@marine.org).'
      );
      assert.equal(
        validateEmail('user@'),
        'Please enter a valid scientific email address (e.g. researcher@marine.org).'
      );
      assert.equal(
        validateEmail('@domain.com'),
        'Please enter a valid scientific email address (e.g. researcher@marine.org).'
      );
      assert.equal(
        validateEmail('user@domain'),
        'Please enter a valid scientific email address (e.g. researcher@marine.org).'
      );
      assert.equal(
        validateEmail('user name@domain.com'),
        'Please enter a valid scientific email address (e.g. researcher@marine.org).'
      );
    });

    it('accepts valid email addresses', () => {
      assert.equal(validateEmail('researcher@orca-marine.org'), '');
      assert.equal(validateEmail('sylvia.earle@noaa.gov'), '');
      assert.equal(validateEmail('ocean_data.telemetry+tag@subsea.co.uk'), '');
      assert.ok(REGEX_EMAIL.test('admin@marine.org'));
    });
  });

  describe('3. Password Strength Regex Validation', () => {
    it('rejects empty password', () => {
      assert.equal(validatePassword(''), 'Password is required.');
      assert.equal(validatePassword(null), 'Password is required.');
    });

    it('rejects password shorter than 8 characters', () => {
      assert.equal(
        validatePassword('Ocean#1'),
        'Password must be at least 8 characters, including 1 uppercase, 1 lowercase, 1 number, and 1 special character.'
      );
    });

    it('rejects password missing uppercase letter', () => {
      assert.equal(
        validatePassword('ocean#marine2026'),
        'Password must be at least 8 characters, including 1 uppercase, 1 lowercase, 1 number, and 1 special character.'
      );
    });

    it('rejects password missing lowercase letter', () => {
      assert.equal(
        validatePassword('OCEAN#MARINE2026'),
        'Password must be at least 8 characters, including 1 uppercase, 1 lowercase, 1 number, and 1 special character.'
      );
    });

    it('rejects password missing number', () => {
      assert.equal(
        validatePassword('Ocean#MarineTele'),
        'Password must be at least 8 characters, including 1 uppercase, 1 lowercase, 1 number, and 1 special character.'
      );
    });

    it('rejects password missing special character', () => {
      assert.equal(
        validatePassword('OceanMarine2026'),
        'Password must be at least 8 characters, including 1 uppercase, 1 lowercase, 1 number, and 1 special character.'
      );
    });

    it('accepts strong password meeting all criteria', () => {
      assert.equal(validatePassword('Ocean#Marine2026'), '');
      assert.equal(validatePassword('Orca!2026Secure'), '');
      assert.equal(validatePassword('Vessel_Guard9@Sea'), '');
      assert.ok(REGEX_PASSWORD.test('Marine$Science99'));
    });
  });

  describe('4. Confirm Password Matching Validation', () => {
    it('rejects empty confirm password', () => {
      assert.equal(
        validateConfirmPassword('', 'Ocean#Marine2026'),
        'Please confirm your password.'
      );
    });

    it('rejects mismatched passwords', () => {
      assert.equal(
        validateConfirmPassword('Different#123', 'Ocean#Marine2026'),
        'Passwords do not match.'
      );
    });

    it('accepts matching passwords', () => {
      assert.equal(
        validateConfirmPassword('Ocean#Marine2026', 'Ocean#Marine2026'),
        ''
      );
    });
  });

  describe('5. Login Password Validation', () => {
    it('rejects empty login password', () => {
      assert.equal(validateLoginPassword(''), 'Password is required.');
    });

    it('rejects password shorter than 6 characters', () => {
      assert.equal(validateLoginPassword('12345'), 'Password must be at least 6 characters.');
    });

    it('accepts valid login password', () => {
      assert.equal(validateLoginPassword('123456'), '');
      assert.equal(validateLoginPassword('Ocean#Marine2026'), '');
    });
  });

  describe('6. Real-time Password Requirements Checklist', () => {
    it('evaluates all 5 security criteria accurately', () => {
      const emptyChecks = checkPasswordRequirements('');
      assert.equal(emptyChecks.length, 5);
      assert.ok(emptyChecks.every((c) => c.met === false));

      const partialChecks = checkPasswordRequirements('Ocean');
      // Length < 8 (false), Upper (true), Lower (true), Number (false), Symbol (false)
      assert.equal(partialChecks.find((c) => c.label.includes('8 characters')).met, false);
      assert.equal(partialChecks.find((c) => c.label.includes('uppercase')).met, true);
      assert.equal(partialChecks.find((c) => c.label.includes('lowercase')).met, true);
      assert.equal(partialChecks.find((c) => c.label.includes('numeric')).met, false);
      assert.equal(partialChecks.find((c) => c.label.includes('special')).met, false);

      const fullChecks = checkPasswordRequirements('Ocean#Marine2026');
      assert.ok(fullChecks.every((c) => c.met === true));
    });
  });
});
