/**
 * Alternative load test using k6 (https://k6.io).
 * Install k6, start services, then run:
 *   k6 run load-tests/k6_booking_test.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BOOKING_URL || 'http://127.0.0.1:8000';

export const options = {
  scenarios: {
    load_10:  { executor: 'constant-vus', vus: 10,  duration: '30s', startTime: '0s' },
    load_50:  { executor: 'constant-vus', vus: 50,  duration: '30s', startTime: '35s' },
    load_200: { executor: 'constant-vus', vus: 200, duration: '30s', startTime: '70s' },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'],
  },
};

let token = '';

export function setup() {
  const res = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
    username: 'dr.smith',
    password: 'clinician1',
  }), { headers: { 'Content-Type': 'application/json' } });
  return { token: res.json('access_token') };
}

export default function (data) {
  const res = http.get(`${BASE_URL}/slots/available?clinic_id=CLINIC-SYD`, {
    headers: { Authorization: `Bearer ${data.token}` },
  });
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(0.1);
}
