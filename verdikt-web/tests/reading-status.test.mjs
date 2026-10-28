import test from 'node:test';
import assert from 'node:assert/strict';
import { fileReadingLabel, fileReadingWarning } from '../src/cabinet/fileReadingPresentation.ts';

test('unreadable files never receive a successful reading label', () => {
  for (const status of ['empty', 'error', 'unsupported', 'pending']) {
    const label = fileReadingLabel({pages: 2, recognition: status});
    assert.doesNotMatch(label, /Text read|pages read/);
  }
  assert.match(fileReadingLabel({pages: 0, recognition:'ok'}), /Text read/);
  assert.match(fileReadingLabel({pages: 2, recognition:'partial'}), /Partially read/);
});

test('warnings describe reading limitations without inventing case facts', () => {
  assert.match(fileReadingWarning('empty'), /OCR|readable copy/);
  assert.match(fileReadingWarning('error'), /could not be read/);
  assert.match(fileReadingWarning('unsupported'), /not supported/);
  assert.match(fileReadingWarning('partial'), /incomplete/);
  assert.equal(fileReadingWarning('ok'), null);
  assert.equal(fileReadingWarning('pending'), null);
});
