import { createI18n } from 'vue-i18n'

const messages = {
  ru: {
    // Navigation
    nav: {
      dashboard: 'Панель управления',
      chat: 'Чат',
      services: 'Сервисы',
      llm: 'LLM',
      tts: 'Голос',
      faq: 'FAQ',
      finetune: 'Обучение',
      monitoring: 'Мониторинг',
      settings: 'Настройки',
      search: 'Поиск...',
      logout: 'Выход'
    },
    // Dashboard
    dashboard: {
      title: 'Панель управления',
      allOperational: 'Все системы работают',
      someServicesStopped: 'Некоторые сервисы остановлены',
      systemError: 'Ошибка системы',
      statusUnknown: 'Статус неизвестен',
      running: 'Запущено',
      stopped: 'Остановлено',
      errors: 'Ошибки',
      gpuMemory: 'Память GPU',
      gpuLoad: 'Нагрузка GPU',
      avgResponse: 'Среднее время',
      totalRequests: 'Всего запросов',
      services: 'Сервисы',
      refresh: 'Обновить',
      quickActions: 'Быстрые действия',
      llmSettings: 'Настройки LLM',
      configureModel: 'Настроить модель',
      voiceSettings: 'Настройки голоса',
      changeVoice: 'Изменить голос',
      faqEditor: 'Редактор FAQ',
      editResponses: 'Редактировать ответы',
      fineTuning: 'Дообучение',
      trainModel: 'Обучить модель',
      health: 'Здоровье компонентов'
    },
    // Services
    services: {
      title: 'Сервисы',
      startAll: 'Запустить все',
      stopAll: 'Остановить все',
      start: 'Запустить',
      stop: 'Остановить',
      restart: 'Перезапустить',
      viewLogs: 'Просмотр логов',
      status: 'Статус',
      pid: 'PID',
      memory: 'Память',
      port: 'Порт'
    },
    // LLM
    llm: {
      title: 'Настройки LLM',
      backend: 'Бэкенд',
      persona: 'Персона',
      parameters: 'Параметры',
      temperature: 'Температура',
      maxTokens: 'Макс. токенов',
      topP: 'Top P',
      repetitionPenalty: 'Штраф повтора',
      systemPrompt: 'Системный промпт',
      resetPrompt: 'Сбросить промпт'
    },
    // TTS
    tts: {
      title: 'Настройки голоса',
      currentVoice: 'Текущий голос',
      voices: 'Голоса',
      presets: 'Пресеты',
      customPresets: 'Пользовательские пресеты',
      testVoice: 'Тест голоса',
      createPreset: 'Создать пресет',
      speed: 'Скорость'
    },
    // FAQ
    faq: {
      title: 'Редактор FAQ',
      addEntry: 'Добавить запись',
      trigger: 'Триггер',
      response: 'Ответ',
      edit: 'Редактировать',
      delete: 'Удалить',
      reload: 'Перезагрузить',
      save: 'Сохранить',
      test: 'Тестировать',
      noResults: 'Нет результатов'
    },
    // Finetune
    finetune: {
      title: 'Дообучение модели',
      dataset: 'Датасет',
      uploadDataset: 'Загрузить датасет',
      processDataset: 'Обработать датасет',
      augmentDataset: 'Аугментировать',
      datasetStats: 'Статистика датасета',
      training: 'Обучение',
      config: 'Конфигурация',
      startTraining: 'Начать обучение',
      stopTraining: 'Остановить',
      progress: 'Прогресс',
      adapters: 'Адаптеры',
      activateAdapter: 'Активировать',
      deleteAdapter: 'Удалить'
    },
    // Monitoring
    monitoring: {
      title: 'Мониторинг',
      gpuStats: 'GPU статистика',
      systemStats: 'Системная статистика',
      errorLog: 'Журнал ошибок',
      clearErrors: 'Очистить'
    },
    // Common
    common: {
      save: 'Сохранить',
      cancel: 'Отмена',
      delete: 'Удалить',
      edit: 'Редактировать',
      add: 'Добавить',
      close: 'Закрыть',
      confirm: 'Подтвердить',
      loading: 'Загрузка...',
      error: 'Ошибка',
      success: 'Успешно',
      warning: 'Внимание',
      info: 'Информация',
      search: 'Поиск',
      filter: 'Фильтр',
      export: 'Экспорт',
      import: 'Импорт',
      settings: 'Настройки'
    },
    // Auth
    auth: {
      login: 'Вход',
      logout: 'Выход',
      username: 'Имя пользователя',
      password: 'Пароль',
      signIn: 'Войти',
      signingIn: 'Вход...',
      invalidCredentials: 'Неверные учётные данные',
      welcome: 'Добро пожаловать'
    },
    // Themes
    themes: {
      light: 'Светлая',
      dark: 'Тёмная',
      system: 'Системная',
      'night-eyes': 'Ночной режим'
    }
  },
  en: {
    // Navigation
    nav: {
      dashboard: 'Dashboard',
      chat: 'Chat',
      services: 'Services',
      llm: 'LLM',
      tts: 'TTS',
      faq: 'FAQ',
      finetune: 'Fine-tune',
      monitoring: 'Monitoring',
      settings: 'Settings',
      search: 'Search...',
      logout: 'Logout'
    },
    // Dashboard
    dashboard: {
      title: 'Dashboard',
      allOperational: 'All Systems Operational',
      someServicesStopped: 'Some Services Stopped',
      systemError: 'System Error',
      statusUnknown: 'Status Unknown',
      running: 'Running',
      stopped: 'Stopped',
      errors: 'Errors',
      gpuMemory: 'GPU Memory',
      gpuLoad: 'GPU Load',
      avgResponse: 'Avg Response',
      totalRequests: 'Total Requests',
      services: 'Services',
      refresh: 'Refresh',
      quickActions: 'Quick Actions',
      llmSettings: 'LLM Settings',
      configureModel: 'Configure model',
      voiceSettings: 'Voice Settings',
      changeVoice: 'Change voice',
      faqEditor: 'FAQ Editor',
      editResponses: 'Edit responses',
      fineTuning: 'Fine-tuning',
      trainModel: 'Train model',
      health: 'Components Health'
    },
    // Services
    services: {
      title: 'Services',
      startAll: 'Start All',
      stopAll: 'Stop All',
      start: 'Start',
      stop: 'Stop',
      restart: 'Restart',
      viewLogs: 'View Logs',
      status: 'Status',
      pid: 'PID',
      memory: 'Memory',
      port: 'Port'
    },
    // LLM
    llm: {
      title: 'LLM Settings',
      backend: 'Backend',
      persona: 'Persona',
      parameters: 'Parameters',
      temperature: 'Temperature',
      maxTokens: 'Max Tokens',
      topP: 'Top P',
      repetitionPenalty: 'Repetition Penalty',
      systemPrompt: 'System Prompt',
      resetPrompt: 'Reset Prompt'
    },
    // TTS
    tts: {
      title: 'Voice Settings',
      currentVoice: 'Current Voice',
      voices: 'Voices',
      presets: 'Presets',
      customPresets: 'Custom Presets',
      testVoice: 'Test Voice',
      createPreset: 'Create Preset',
      speed: 'Speed'
    },
    // FAQ
    faq: {
      title: 'FAQ Editor',
      addEntry: 'Add Entry',
      trigger: 'Trigger',
      response: 'Response',
      edit: 'Edit',
      delete: 'Delete',
      reload: 'Reload',
      save: 'Save',
      test: 'Test',
      noResults: 'No results'
    },
    // Finetune
    finetune: {
      title: 'Model Fine-tuning',
      dataset: 'Dataset',
      uploadDataset: 'Upload Dataset',
      processDataset: 'Process Dataset',
      augmentDataset: 'Augment',
      datasetStats: 'Dataset Statistics',
      training: 'Training',
      config: 'Configuration',
      startTraining: 'Start Training',
      stopTraining: 'Stop',
      progress: 'Progress',
      adapters: 'Adapters',
      activateAdapter: 'Activate',
      deleteAdapter: 'Delete'
    },
    // Monitoring
    monitoring: {
      title: 'Monitoring',
      gpuStats: 'GPU Statistics',
      systemStats: 'System Statistics',
      errorLog: 'Error Log',
      clearErrors: 'Clear'
    },
    // Common
    common: {
      save: 'Save',
      cancel: 'Cancel',
      delete: 'Delete',
      edit: 'Edit',
      add: 'Add',
      close: 'Close',
      confirm: 'Confirm',
      loading: 'Loading...',
      error: 'Error',
      success: 'Success',
      warning: 'Warning',
      info: 'Info',
      search: 'Search',
      filter: 'Filter',
      export: 'Export',
      import: 'Import',
      settings: 'Settings'
    },
    // Auth
    auth: {
      login: 'Login',
      logout: 'Logout',
      username: 'Username',
      password: 'Password',
      signIn: 'Sign in',
      signingIn: 'Signing in...',
      invalidCredentials: 'Invalid credentials',
      welcome: 'Welcome'
    },
    // Themes
    themes: {
      light: 'Light',
      dark: 'Dark',
      system: 'System',
      'night-eyes': 'Night Eyes'
    }
  }
}

export const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('admin_locale') || 'ru',
  fallbackLocale: 'en',
  messages
})

export function setLocale(locale: 'ru' | 'en') {
  i18n.global.locale.value = locale
  localStorage.setItem('admin_locale', locale)
}

export function getLocale(): 'ru' | 'en' {
  return i18n.global.locale.value as 'ru' | 'en'
}
