// Rebuild in an Artifact Session with its callback-scoped presentation facade.
// Screenshots are evidence captured from the running application, not mockups.
export default async function buildDefense(presentation, root) {
  presentation.slides.keep([]);
  const red = '#ED2035', ink = '#141B2B', muted = '#67748B';
  const box = (slide, x, y, w, h, fill, stroke = 'none') => slide.shapes.add({
    geometry: 'rect', position: {left:x,top:y,width:w,height:h}, fill,
    line: {fill:stroke,width:stroke === 'none' ? 0 : 1},
  });
  const text = (slide, content, x, y, w, h, size = 28, color = ink, bold = false) => {
    const shape = box(slide,x,y,w,h,'none');shape.text=content;
    shape.text.style={fontSize:size,typeface:'Arial',color,bold};return shape;
  };
  const picture = (slide, file, x, y, w, h, fit = 'contain') => slide.images.add({
    path:root+'/'+file,alt:file.includes('screens') ? 'Экран работающего прототипа Альфа.Поток' : 'Иллюстрация бизнеса, актив проекта',
    position:{left:x,top:y,width:w,height:h},fit,
  });
  const newSlide = (title, label, notes) => {
    const slide=presentation.slides.add();slide.background.fill='#F7F8FB';
    text(slide,'ITigers / Альфа.Поток',64,30,700,30,18,red,true);
    text(slide,title,64,82,1152,108,44,ink,true);
    text(slide,label,64,664,1050,25,16,muted);
    text(slide,String(presentation.slides.items.length).padStart(2,'0'),1150,664,65,25,16,muted);
    slide.speakerNotes.text=notes;return slide;
  };
  let s = newSlide('Умный кредитный кабинет', 'Прототип для хакатона · 2026',
    '0:00–0:20. Здравствуйте! Мы ITigers. Представляем Альфа.Поток — единый путь клиента и банка до демонстрационной выдачи. Источники: README.md, docs/DEFENSE.md; визуал frontend/public/images/hero-card.png создан для проекта. Все данные синтетические.');
  text(s,'Альфа.Поток',64,252,640,90,64,ink,true);
  text(s,'Понятный путь заявки\nдля предпринимателя и банка',66,370,620,110,31,muted);
  text(s,'Команда ITigers',66,548,620,50,30,red,true);
  picture(s,'frontend/public/images/hero-card.png',770,206,445,405,'cover');

  s=newSlide('Задачи клиента и банка','Основание — кейс; потребности требуют проверки на интервью',
    '0:20–0:45. Источник: docs/Альфа_Хак_Умный_кредитный_кабинет_Задание.pdf, страницы 4–8; docs/PRODUCT.md. Разобраны роли и процесс, интервью не проводились. Нельзя заявлять подтверждённый CustDev или экономический эффект.');
  text(s,'Предприниматель',64,222,530,48,34,red,true);
  text(s,'Выбрать подходящие условия\n\nПонять результат и следующий шаг\n\nПродолжить заявку без потери данных',64,304,530,300,28);
  text(s,'Сотрудник банка',690,222,525,48,34,red,true);
  text(s,'Видеть данные и риск вместе\n\nЗапросить конкретное уточнение\n\nПредложить другие условия',690,304,525,300,28);

  s=newSlide('Кабинет предпринимателя','Реальный экран прототипа · данные демонстрационные',
    '0:45–1:15. Три продукта, предзаполненная компания, калькулятор, предварительный ML, сохранённая заявка, история и новости. Источники: frontend/src/pages, backend/api, docs/hackathon/screens/dashboard.png (локальный E2E 24.10.2026).');
  picture(s,'docs/hackathon/screens/dashboard.png',64,204,790,426);
  text(s,'3 продукта',894,220,320,46,34,red,true);
  text(s,'Параметры и оценка\nдо отправки\n\nСтатус и действие\nпосле решения\n\nСтатьи по отрасли',894,287,320,320,27);

  s=newSlide('Дозапрос и встречные условия','Одна заявка, сохранённая история и явное согласие клиента',
    '1:15–1:45. Ответ с файлом и уточнёнными показателями возвращается сотруднику. Встречный оффер хранится отдельно; исходные 2 млн остаются в заявке, принятые 900 тыс. используются в выдаче. Источники: completion.py, STATES.md и реальные E2E-экраны в docs/hackathon/screens.');
  text(s,'Уточнение сведений',64,203,540,40,28,red,true);
  text(s,'Другие условия банка',676,203,540,40,28,red,true);
  picture(s,'docs/hackathon/screens/info-request.png',64,257,540,366);
  picture(s,'docs/hackathon/screens/counter.png',676,257,540,366);

  s=newSlide('Архитектура и кредитное решение','Модель оценивает риск; правила и движение заявки находятся в Django',
    '1:45–2:15. Редактируемая схема, источник docs/ARCHITECTURE.md. HTTPS Nginx проксирует статический Vue и Django API. Django хранит SQLite и вызывает неизменённый ML по внутреннему HTTP. Таймаут 2.5с приводит к ручному рассмотрению без выдуманного score. ML-файлы не изменены относительно 50af371.');
  const node=(title,sub,x,y,w=300)=>{box(s,x,y,w,112,'#FFFFFF','#DCE2EB');text(s,title,x+20,y+18,w-40,40,title.includes('LightGBM') ? 24 : 29,ink,true);text(s,sub,x+20,y+65,w-40,32,19,muted);};
  node('Vue 3','Клиент и сотрудник',64,235);text(s,'→',382,266,80,60,40,red,true);
  node('Django / DRF','Процесс и политика',490,235);text(s,'→',808,266,80,60,40,red,true);
  node('FastAPI / LightGBM','Исходный код без правок',916,235);
  text(s,'HTTPS / API',366,221,125,28,17,muted);text(s,'HTTP, 2.5 с',793,221,125,28,17,muted);
  text(s,'↓',610,366,60,50,36,red,true);node('SQLite','Заявка, аудит, PDF, оффер',490,430);
  text(s,'Компания / БКИ\nсинтетические данные',64,452,340,90,25,muted);
  text(s,'Недоступность ML\n→ ручное рассмотрение',916,452,300,90,25,red,true);
  text(s,'GitHub Actions → проверки → три образа → изолированный Compose',64,594,1152,43,24,ink,true);

  s=newSlide('Проверка и границы прототипа','Docker Compose · GitHub Actions · HTTPS',
    '2:15–2:40. На момент подготовки python -m pytest с ML_INTEGRATION=1: 29 passed. CI повторяет реальные inference-тесты и проверку схемы/миграций. Браузерный E2E покрывает основные ветви и ширину 390 px. Источники: tests, test_pipeline.py, test_completion.py, workflow; docs/TEST_SCENARIOS.md. Это функциональная проверка, не замер банковской точности/нагрузки.');
  text(s,'29',64,212,260,130,96,red,true);text(s,'автотестов, включая\nинтеграцию с реальным ML',340,229,825,100,35,ink,true);
  text(s,'Роли и чужие документы',64,390,530,48,28,ink,true);
  text(s,'Повторная подпись → одна выдача',64,458,1125,48,28,ink,true);
  text(s,'Ошибка ML → сохранённая заявка у сотрудника',64,526,1125,48,28,ink,true);
  text(s,'БКИ, реестры, подпись и перевод денег смоделированы',64,601,1152,38,22,red);

  s=newSlide('Живой показ: заявка → результат','alpha.srv-node.com · профиль «Пекарня Зерно»',
    '2:40–3:40. Открыть сайт: green → 2 млн,24 мес → отправить → принять → PDF → согласие → подписать → DISBURSED. На слайде реальные резервные скриншоты. Если показ недоступен, честно назвать их скриншотами. Источники docs/TEST_SCENARIOS.md, DEFENSE.md и E2E-экраны signing/issued.');
  text(s,'Условия → PDF → согласие',64,216,540,45,28,red,true);
  picture(s,'docs/hackathon/screens/signing.png',64,284,540,295);
  text(s,'Сохранённая демовыдача',676,216,540,45,28,red,true);
  picture(s,'docs/hackathon/screens/issued.png',676,284,540,295);
  text(s,'Обновление страницы сохраняет результат и историю',64,607,1152,40,25,ink,true);

  s=newSlide('Альфа.Поток · ITigers','Следующий шаг: интервью, реальные интеграции и банковская валидация ML',
    '3:40–4:00. Единый работающий процесс для клиента и банка. Код, Swagger, диаграммы, коллекция запросов, сценарии и Docker доступны в публичном репозитории. Не обещать внедрение/эффект без реальных данных. Следующие слайды — только по вопросам.');
  text(s,'Клиент знает следующий шаг.\nБанк видит контекст решения.',64,228,1152,145,46,ink,true);
  text(s,'Открыть прототип',64,433,1100,40,25,muted);
  text(s,'alpha.srv-node.com',64,486,1130,55,38,red,true);
  text(s,'github.com/Favck/alfa-smart-credit',64,571,1140,46,28,ink);

  s=newSlide('Ограничения исходной ML-модели','Приложение · только по вопросам жюри',
    'Источники: ml/app/model.py, ml/train.py, docs/ML_INTEGRATION.md. Исходные метаданные /model описывают LogisticRegression и 14 признаков; фактический файл LightGBM имеет 15, evaluate сообщает risk_scorecard_v1.0. Эти расхождения сохранены, а не скрыто исправлены. Сборка фиксируется Git SHA, веса по SHA256.');
  text(s,'Синтетическое обучение',64,220,1152,45,31,red,true);
  text(s,'Нет доказательства точности и калибровки на реальных заёмщиках',64,280,1130,65,27);
  text(s,'Фиксированные 22% внутри расчёта риска',64,374,1152,45,31,red,true);
  text(s,'Ставки продукта и оффера считаются отдельно в Django',64,434,1130,50,27);
  text(s,'100 − PD — выход модели, не гарантия одобрения',64,529,1152,80,31,ink,true);

  s=newSlide('Материалы для самостоятельной проверки','Приложение · репозиторий публичный',
    'Источники: README.md и соответствующие файлы репозитория. Дедлайн организаторов неизвестен, тег фиксирует подготовленную версию и не доказывает соблюдение срока. Данные реальные клиентские не используются.');
  text(s,'Запуск и API',64,220,530,45,32,red,true);
  text(s,'README + Docker Compose\n\nSwagger + OpenAPI\n\nКоллекция Postman\n\nСинтетические профили и PDF',64,292,530,300,27);
  text(s,'Процесс и защита',690,220,525,45,32,red,true);
  text(s,'Архитектура + модель данных\n\nСостояния + сценарии\n\nПродуктовые гипотезы\n\nРечь, демонстрация и Q&A',690,292,525,300,27);
  return {slideCount:presentation.slides.items.length};
}
