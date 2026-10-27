import test from 'node:test';
import assert from 'node:assert/strict';
import { api, mapAnalysis } from '../src/api/client.ts';

test('null legal fields stay null and warnings survive mapping', () => {
  const result = mapAnalysis({ schema_version: 1, stats: {documents: 1, pages: 0, seconds: 1},
    prompt: 'Check', fabula: 'Summary', qualification: null, scale: null, draft: null,
    mitigating: [], variants: [], similar: [], warnings: ['Partial extraction'], legal_checks: [] });
  assert.equal(result.scale, null);
  assert.equal(result.draft, null);
  assert.equal(result.qualification, null);
  assert.deepEqual(result.warnings, ['Partial extraction']);
});

test('server validation error is readable', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({detail: 'Unsupported format'}), {status: 415});
  try { await assert.rejects(api.listCases(), /Unsupported format/); }
  finally { globalThis.fetch = original; }
});

test('sending a case uploads original bytes and text using backend field names', async () => {
  const original = globalThis.fetch;
  let request;
  globalThis.fetch = async (url, options) => {
    request = {url, ...options};
    return new Response(JSON.stringify({assistant_message:{id:7}}), {status:202});
  };
  try {
    await api.sendCase('3', 'Check this verdict', [new File(['tail evidence'], 'verdict.txt')]);
    assert.equal(request.url, '/api/chats/3/messages');
    assert.equal(request.body.get('content'), 'Check this verdict');
    assert.equal(await request.body.get('files').text(), 'tail evidence');
    assert.equal(request.body.get('use_knowledge_base'), 'false');
  } finally { globalThis.fetch = original; }
});
