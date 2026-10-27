async page => {
  await page.setViewportSize({width:1440,height:1000});
  await page.route('**/api/chats', route => route.fulfill({status:503,contentType:'application/json',body:'{"detail":"Service temporarily unavailable"}'}));
  await page.goto('http://127.0.0.1:5178/app');
  await page.getByRole('alert').filter({hasText:'Service temporarily unavailable'}).waitFor();
  await page.unroute('**/api/chats');
  await page.getByRole('button', {name:'Retry cases'}).click();
  await page.getByRole('alert').waitFor({state:'hidden'});
  await page.goto('http://127.0.0.1:5178/app/case/999999/result');
  await page.getByRole('alert').waitFor();
  if (await page.locator('.result').count()) throw Error('Missing case shows a fabricated result');
  await page.goto('http://127.0.0.1:5178/app');
  await page.locator('input[type=file]').first().evaluate(input => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['invalid format'], 'invalid.exe', {type:'application/octet-stream'}));
    input.files = transfer.files;
    input.dispatchEvent(new Event('change', {bubbles:true}));
  });
  await page.getByRole('button', {name:'Отправить',exact:true}).click();
  await page.getByRole('alert').filter({hasText:'не поддерживается'}).waitFor();
  if (!await page.getByRole('button', {name:'Удалить файл invalid.exe'}).count()) throw Error('Rejected upload lost its retry state');
  return {networkError:'visible and retryable',missingCase:'no fabricated result',unsupportedUpload:'visible and retained'};
}
