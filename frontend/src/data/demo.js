export const money = (value) =>
  `${Math.round(value).toLocaleString('ru-RU')} ₽`

export const products = [
  {
    id: 'working_capital',
    name: 'Оборотный кредит',
    description: 'На закупку сырья, товаров и развитие бизнеса',
    minAmount: 500000,
    maxAmount: 5000000,
    minTerm: 6,
    maxTerm: 36,
    rate: 22,
    icon: '↗',
    purpose: 'Закупить товары',
  },
  {
    id: 'equipment_purchase',
    name: 'Кредит на оборудование',
    description: 'Для покупки техники и модернизации производства',
    minAmount: 1000000,
    maxAmount: 10000000,
    minTerm: 12,
    maxTerm: 60,
    rate: 19,
    icon: '⚙',
    purpose: 'Купить оборудование',
  },
  {
    id: 'overdraft',
    name: 'Овердрафт',
    description: 'Для временных кассовых разрывов',
    minAmount: 50000,
    maxAmount: 3000000,
    minTerm: 1,
    maxTerm: 12,
    rate: 24,
    icon: '⇄',
    purpose: 'Закрыть кассовый разрыв',
  },
]

export const profiles = [
  {
    id: 'green',
    name: 'Иван',
    fullName: 'Иванов Иван Петрович',
    role: 'client',
    company: 'ООО «Пекарня Зерно»',
    inn: '7701234567',
    ogrn: '1207700123456',
    industry: 'Производство хлебобулочных изделий',
    category: 'Производство',
    revenue: 1500000,
    payments: 40000,
    description: 'Клиент · зелёный сценарий',
  },
  {
    id: 'yellow',
    name: 'Алексей',
    fullName: 'Смирнов Алексей Викторович',
    role: 'client',
    company: 'ИП Смирнов А.В.',
    inn: '780234567890',
    ogrn: '322780000123456',
    industry: 'Розничная торговля',
    category: 'Торговля',
    revenue: 600000,
    payments: 180000,
    description: 'Клиент · пограничный сценарий',
  },
  {
    id: 'red',
    name: 'Пётр',
    fullName: 'Петров Пётр Петрович',
    role: 'client',
    company: 'ООО «СтройВектор»',
    inn: '5003456789',
    ogrn: '1215000123456',
    industry: 'Строительство',
    category: 'Строительство',
    revenue: 300000,
    payments: 120000,
    description: 'Клиент · красный сценарий',
  },
  {
    id: 'underwriter',
    name: 'Анна',
    fullName: 'Анна Аналитик',
    role: 'bank',
    company: 'Кабинет сотрудника банка',
    description: 'Андеррайтер · очередь и решения',
  },
]

export const pages = {
  home: { icon: '⌂', title: 'Главная' },
  products: { icon: '▦', title: 'Продукты' },
  apply: { icon: '＋', title: 'Новая заявка' },
  applications: { icon: '☷', title: 'Мои заявки' },
  news: { icon: '◈', title: 'Новости' },
  profile: { icon: '◉', title: 'Компания' },
  queue: { icon: '☷', title: 'Очередь' },
  detail: { icon: '◎', title: 'Анализ заявки' },
}

export const steps = [
  { title: 'Заявка отправлена', description: 'Заявка зарегистрирована' },
  { title: 'Проверка данных', description: 'Проверены данные компании' },
  {
    title: 'Оценка рисков',
    description: 'ML оценивает финансовые показатели',
  },
  { title: 'Решение банка', description: 'Формируется результат' },
  { title: 'Подписание и выдача', description: 'Заключительный этап' },
]

export const news = [
  {
    id: 1,
    category: 'Торговля',
    title: 'Как подготовиться к сезонному росту спроса',
  },
  {
    id: 2,
    category: 'Производство',
    title: 'Финансирование покупки оборудования',
  },
  { id: 3, category: 'Финансы', title: 'Как оценить долговую нагрузку' },
  { id: 4, category: 'Торговля', title: 'Планирование закупок на квартал' },
  {
    id: 5,
    category: 'Строительство',
    title: 'Кассовые разрывы между этапами проекта',
  },
]

export const riskFactors = [
  { title: 'Нет просрочек', impact: 60 },
  { title: 'Стаж бизнеса', impact: 40 },
  { title: 'Долговая нагрузка', impact: -40 },
  { title: 'Срок кредита', impact: -10 },
]

export function createCases() {
  return [
    {
      id: 'APP-1042',
      company: profiles[0].company,
      amount: 2000000,
      score: 670,
      risk: 'Низкий',
      decision: '',
    },
    {
      id: 'APP-1043',
      company: profiles[1].company,
      amount: 4500000,
      score: 558,
      risk: 'Средний',
      decision: '',
    },
    {
      id: 'APP-1044',
      company: profiles[2].company,
      amount: 1200000,
      score: 410,
      risk: 'Высокий',
      decision: '',
    },
  ]
}

export function createDraft(profile) {
  return {
    productId: 'working_capital',
    amount: 2000000,
    months: 24,
    purpose: 'Закупка печей и сырья',
    revenue: profile.revenue,
    payments: profile.payments,
  }
}
