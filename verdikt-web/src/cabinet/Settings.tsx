import { useState, type ReactNode } from 'react';

type Tab = 'profile' | 'prefs' | 'security' | 'data';
type ToggleKey = 'regionOnly' | 'notify' | 'twofa' | 'autodelete' | 'noTraining';

const TABS: [Tab, string][] = [
  ['profile', 'Профиль'],
  ['prefs', 'Предпочтения'],
  ['security', 'Безопасность'],
  ['data', 'Данные'],
];

const PROFILE_FIELDS: [string, string, string][] = [
  ['firstName', 'Имя', 'Имя'],
  ['lastName', 'Фамилия', 'Фамилия'],
  ['email', 'Email', 'name@example.ru'],
  ['position', 'Должность', 'Например, помощник судьи'],
  ['org', 'Суд или организация', 'Название'],
  ['region', 'Регион', 'Регион'],
];

const TOGGLES: Record<ToggleKey, [string, string]> = {
  regionOnly: ['Практика только моего региона', 'Схожие приговоры подбираются в первую очередь из вашего региона'],
  notify: ['Уведомлять, когда проект готов', 'Письмо на email после завершения анализа'],
  twofa: ['Двухфакторная аутентификация', 'Код подтверждения при входе с нового устройства'],
  autodelete: ['Удалять материалы через 30 дней', 'Проекты приговоров сохранятся, исходные файлы — нет'],
  noTraining: ['Не использовать мои дела для улучшения сервиса', 'Материалы не попадают в обучение моделей'],
};

const SESSIONS = [
  { device: 'MacBook · Chrome', meta: '[Город] · сейчас', current: true },
  { device: 'iPhone · Safari', meta: '[Город] · вчера', current: false },
];

function Row({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <div className="set-row">
      <div>
        <div className="set-title">{title}</div>
        <div className="muted-14">{hint}</div>
      </div>
      {children}
    </div>
  );
}

// TODO(api): there is no auth/user/settings API in the backend yet — everything here is local state.
export function SettingsScreen({ onCancel }: { onCancel: () => void }) {
  const [tab, setTab] = useState<Tab>('profile');
  const [format, setFormat] = useState<'DOCX' | 'PDF'>('DOCX');
  const [toggles, setToggles] = useState<Record<ToggleKey, boolean>>({ regionOnly: true, notify: true, twofa: true, autodelete: false, noTraining: true });
  const [saved, setSaved] = useState(false);

  const sw = (key: ToggleKey) => (
    <Row key={key} title={TOGGLES[key][0]} hint={TOGGLES[key][1]}>
      <button type="button" role="switch" aria-checked={toggles[key]} aria-label={TOGGLES[key][0]} className="switch" onClick={() => setToggles((t) => ({ ...t, [key]: !t[key] }))}>
        <span />
      </button>
    </Row>
  );

  return (
    <div className="fade-in settings">
      <h1 className="screen-h2">Настройки</h1>
      <div role="tablist" aria-label="Разделы настроек" className="seg" style={{ alignSelf: 'flex-start' }}>
        {TABS.map(([id, label]) => (
          <button key={id} type="button" role="tab" id={`tab-${id}`} aria-controls={`panel-${id}`} aria-selected={tab === id} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="fade-in" key={tab}>
        {tab === 'profile' && (
          <div className="set-profile">
            <div className="set-avatar-row">
              <span className="avatar avatar-lg" aria-hidden="true">
                ИП
              </span>
              <button type="button" className="btn btn-soft btn-sm">
                Изменить фото
              </button>
            </div>
            <div className="set-fields">
              {PROFILE_FIELDS.map(([name, label, placeholder]) => (
                <label key={name} className="set-field">
                  <span>{label}</span>
                  <input type={name === 'email' ? 'email' : 'text'} name={name} placeholder={placeholder} />
                </label>
              ))}
            </div>
          </div>
        )}

        {tab === 'prefs' && (
          <div className="set-list">
            <Row title="Регион практики" hint="По нему подбираются схожие приговоры и среднее по практике">
              <label className="set-select">
                <span className="sr-only">Регион практики</span>
                <select defaultValue="">
                  <option value="" disabled>
                    [Регион]
                  </option>
                </select>
              </label>
            </Row>
            <Row title="Формат проекта приговора" hint="В каком виде скачивать готовый проект">
              <div role="group" aria-label="Формат" className="seg">
                {(['DOCX', 'PDF'] as const).map((f) => (
                  <button key={f} type="button" aria-pressed={format === f} onClick={() => setFormat(f)}>
                    {f}
                  </button>
                ))}
              </div>
            </Row>
            {sw('regionOnly')}
            {sw('notify')}
          </div>
        )}

        {tab === 'security' && (
          <div className="set-list">
            <Row title="Пароль" hint="Последнее изменение — [дата]">
              <button type="button" className="btn btn-line btn-sm">
                Изменить
              </button>
            </Row>
            {sw('twofa')}
            <div className="set-sessions">
              <div className="set-title">Активные сеансы</div>
              {SESSIONS.map((s) => (
                <div key={s.device} className="session">
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{s.device}</div>
                    <div style={{ fontSize: 13, color: '#707070' }}>{s.meta}</div>
                  </div>
                  {s.current ? (
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#707070' }}>Этот сеанс</span>
                  ) : (
                    <button type="button" className="btn btn-line btn-xs">
                      Завершить
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'data' && (
          <div className="set-list">
            {sw('autodelete')}
            {sw('noTraining')}
            <Row title="Экспорт данных" hint="Архив со всеми делами и проектами приговоров">
              <button type="button" className="btn btn-line btn-sm">
                Скачать архив
              </button>
            </Row>
            <div className="danger-box">
              <div>
                <div className="set-title" style={{ color: '#b42318' }}>
                  Удалить все дела
                </div>
                <div className="muted-14">Материалы и проекты будут удалены без возможности восстановления</div>
              </div>
              {/* TODO(api): require explicit confirmation before calling a destructive endpoint */}
              <button type="button" className="btn btn-danger btn-sm">
                Удалить
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="set-actions">
        <button type="button" className="btn btn-ink btn-md" onClick={() => setSaved(true)}>
          Сохранить
        </button>
        <button type="button" className="btn btn-soft btn-md" onClick={onCancel}>
          Отмена
        </button>
        <span role="status" className="muted-14">
          {saved ? 'Сохранено локально (нет API)' : ''}
        </span>
      </div>
    </div>
  );
}
