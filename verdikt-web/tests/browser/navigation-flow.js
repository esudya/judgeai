async page => {
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://127.0.0.1:5178/app');
  await page.route('**/api/chats/*/messages', async route => {
    if (route.request().method() !== 'POST') return route.continue();
    const response = await route.fetch();
    await page.waitForTimeout(700);
    await route.fulfill({response});
  });
  await page.getByRole('textbox', {name:'Задача по делу'}).fill('Delayed synthetic request.');
  const response = page.waitForResponse(r => r.url().endsWith('/messages') && r.request().method() === 'POST');
  await page.getByRole('button', {name:'Отправить',exact:true}).click();
  await page.getByRole('button', {name:'Новое дело',exact:true}).click();
  await response;
  await page.waitForTimeout(200);
  await page.unroute('**/api/chats/*/messages');
  if (page.url() !== 'http://127.0.0.1:5178/app') throw Error('Completed request navigated away from the new draft');
  return {navigationDuringSend:'preserves the new draft'};
}
