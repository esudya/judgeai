import test from 'node:test';
import assert from 'node:assert/strict';
import { legalCheckSourceUrl, legalCheckStatusLabel } from '../src/cabinet/legalCheckPresentation.ts';

test('violation, missing data and candidate statuses read differently', () => {
  assert.match(legalCheckStatusLabel('possible_violation'), /Возможное нарушение/);
  assert.equal(legalCheckStatusLabel('insufficient_data'), 'Недостаточно данных');
  assert.match(legalCheckStatusLabel('ok'), /Кандидат/);
});

test('only http sources become links', () => {
  assert.equal(legalCheckSourceUrl('http://pravo.gov.ru/x'), 'http://pravo.gov.ru/x');
  assert.equal(legalCheckSourceUrl('ст. 15 УК РФ, ред. от 04.08.2026'), null);
  assert.equal(legalCheckSourceUrl('javascript:alert(1)'), null);
});
