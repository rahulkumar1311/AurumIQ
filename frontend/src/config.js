/**
 * AurumIQ Frontend Configuration
 * Reads VITE_API_URL from environment variables (e.g. https://aurumiq-1.onrender.com)
 * Defaults to https://aurumiq-1.onrender.com in production mode if unset.
 * Falls back to empty string for relative paths in local Vite proxy development.
 */
export const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? 'https://aurumiq-1.onrender.com' : '')
).replace(/\/+$/, '');

/**
 * Helper to build full API endpoint URL
 * @param {string} endpoint - API path (e.g. '/api/health' or 'api/overview')
 * @returns {string} - Full URL with base URL prefix, or relative path
 */
export function getApiUrl(endpoint) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
}

