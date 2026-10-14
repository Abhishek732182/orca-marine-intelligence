/**
 * ORCA Marine Intelligence — Validation Utilities
 * JavaScript & Regular Expression Validation Rules for Frontend Authentication
 */

export const REGEX_FULL_NAME = /^[a-zA-Z\s'.-]+$/;
export const REGEX_EMAIL = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
// At least 8 characters, including 1 uppercase, 1 lowercase, 1 number, and 1 special character
export const REGEX_PASSWORD = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_+\-=[\]{}|;:,.<>])[A-Za-z\d@$!%*?&#^()_+\-=[\]{}|;:,.<>]{8,}$/;

/**
 * Validates a user's full name.
 * Rule: Not empty, trimmed length >= 2, only letters, spaces, apostrophes, hyphens, and periods.
 */
export function validateFullName(name) {
  if (typeof name !== 'string') {
    return 'Full Name is required.';
  }
  const trimmed = name.trim();
  if (!trimmed) {
    return 'Full Name is required.';
  }
  if (trimmed.length < 2) {
    return 'Full Name must be at least 2 characters long.';
  }
  if (!REGEX_FULL_NAME.test(trimmed)) {
    return 'Full Name can only contain letters, spaces, apostrophes, or hyphens.';
  }
  return '';
}

/**
 * Validates an email address.
 * Rule: Not empty, valid format via regex.
 */
export function validateEmail(email) {
  if (typeof email !== 'string') {
    return 'Email address is required.';
  }
  const trimmed = email.trim();
  if (!trimmed) {
    return 'Email address is required.';
  }
  if (!REGEX_EMAIL.test(trimmed)) {
    return 'Please enter a valid scientific email address (e.g. researcher@marine.org).';
  }
  return '';
}

/**
 * Validates password strength for registration.
 * Rule: Not empty, min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character.
 */
export function validatePassword(password) {
  if (!password) {
    return 'Password is required.';
  }
  if (!REGEX_PASSWORD.test(password)) {
    return 'Password must be at least 8 characters, including 1 uppercase, 1 lowercase, 1 number, and 1 special character.';
  }
  return '';
}

/**
 * Validates confirm password.
 * Rule: Not empty, must match password.
 */
export function validateConfirmPassword(confirmPassword, password) {
  if (!confirmPassword) {
    return 'Please confirm your password.';
  }
  if (confirmPassword !== password) {
    return 'Passwords do not match.';
  }
  return '';
}

/**
 * Validates password for login.
 * Rule: Not empty, minimum 6 characters.
 */
export function validateLoginPassword(password) {
  if (!password) {
    return 'Password is required.';
  }
  if (password.length < 6) {
    return 'Password must be at least 6 characters.';
  }
  return '';
}

/**
 * Detailed password requirements checker for real-time UI meters.
 */
export function checkPasswordRequirements(password = '') {
  return [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'One uppercase letter (A-Z)', met: /[A-Z]/.test(password) },
    { label: 'One lowercase letter (a-z)', met: /[a-z]/.test(password) },
    { label: 'One numeric digit (0-9)', met: /\d/.test(password) },
    {
      label: 'One special character (@$!%*?&...)',
      met: /[@$!%*?&#^()_+\-=[\]{}|;:,.<>]/.test(password),
    },
  ];
}
