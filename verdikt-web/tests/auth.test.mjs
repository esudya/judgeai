import test from 'node:test';
import assert from 'node:assert/strict';
import { api, auth } from '../src/api/client.ts';

test('login uses a custom header and subsequent mutations carry session-bound CSRF', async () => {
  const original = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({url, ...options});
    return new Response(JSON.stringify(url.endsWith('/login')
      ? {id: 1, username: 'alice', is_admin: false, csrf_token: 'csrf-synthetic'} : {}));
  };
  try {
    await auth.login('alice', 'synthetic-password');
    await api.createCase();
    assert.equal(requests[0].headers.get('X-Requested-With'), 'JudgeAI');
    assert.equal(requests[1].headers.get('X-CSRF-Token'), 'csrf-synthetic');
    assert.equal(requests[1].credentials, 'same-origin');
    await auth.logout();
    await api.createCase();
    assert.equal(requests.at(-1).headers.has('X-CSRF-Token'), false);
  } finally { globalThis.fetch = original; }
});

test('failed login and expired sessions do not retain CSRF from a previous user', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({id:1, username:'alice', csrf_token:'old'}));
  try {
    await auth.login('alice', 'synthetic-password');
    globalThis.fetch = async () => new Response(JSON.stringify({detail:'Authentication required'}), {status:401});
    await assert.rejects(auth.me(), /Authentication required/);
    let headers;
    globalThis.fetch = async (_, options) => { headers = options.headers; return new Response('{}'); };
    await api.createCase();
    assert.equal(headers.has('X-CSRF-Token'), false);
  } finally { globalThis.fetch = original; }
});
