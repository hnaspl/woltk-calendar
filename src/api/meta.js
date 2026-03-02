import api from './index'

/**
 * Fetch shared application constants from the backend.
 * GET /api/v1/meta/constants
 */
export function getConstants() {
  return api.get('/meta/constants')
}
