async page => {
  await page.emulateMedia({reducedMotion:'reduce'});
  const failures = [];
  page.on('pageerror', error => failures.push(error.message));
  await page.setViewportSize({width:1440, height:1000});
  await page.goto('http://127.0.0.1:5178/app');
  await page.getByRole('textbox', {name:'Задача по делу'}).fill('Review this synthetic verdict.');
  await page.locator('input[type=file]').first().evaluate(input => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['Synthetic verdict. The defendant admitted guilt. No real personal data.'], 'synthetic-verdict.txt', {type:'text/plain'}));
    input.files = transfer.files;
    input.dispatchEvent(new Event('change', {bubbles:true}));
  });
  await page.getByRole('button', {name:'Отправить', exact:true}).click();
  await page.locator('.result').waitFor({timeout:15000});
  const url = page.url();
  const caseId = url.match(/case\/(\d+)/)[1];
  const response = await page.request.get(`http://127.0.0.1:5178/api/chats/${caseId}/messages`);
  const messages = await response.json();
  if (messages[0].attachments[0].filename !== 'synthetic-verdict.txt') throw Error('Upload missing');
  if (messages[1].status !== 'completed') throw Error('Analysis not completed');
  if ((await page.locator('.legal-check').count()) !== 2) throw Error('Legal checks missing');
  if (await page.locator('.thread-user').count() !== 1) throw Error('Duplicate request bubble');
  await page.reload();
  await page.locator('.result').waitFor();
  await page.screenshot({path:'/tmp/judgeai-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.locator('.cab-side').waitFor({state:'hidden'});
  await page.screenshot({path:'/tmp/judgeai-mobile.png',fullPage:true});
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  if (overflow) throw Error('Mobile horizontal overflow');
  if (failures.length) throw Error(failures.join('\n'));
  return {caseId, uploadedFiles:messages[0].attachments.length, legalChecks:messages[1].result.legal_checks.length, reload:'passed', mobileOverflow:overflow, pageErrors:failures};
}
