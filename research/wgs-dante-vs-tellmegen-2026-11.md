# Dante Labs и tellmeGen Ultra (30x WGS): сравнение для покупателя из Варшавы

Проверено 8 ноября 2026 г. Источники: официальные сайты, справочные центры и юридические документы, Trustpilot (отзывы 2026 г.), DNAGenics, обзорные блоги.
**Не открылись:** h600.org (HTTP 403), таблица h600 в Google Sheets (не прочитана), Genetic Lifehacks (страница 404, статьи сравнения не нашлось), Reddit (поиск не нашёл тредов за 2025–2026 гг.).
Пометки: ❌ — противоречит исходному утверждению, ⚠️ — источники противоречат друг другу, «не подтверждено» — проверить не удалось.

## Таблица сравнения

| # | Пункт | Dante Labs | tellmeGen Ultra |
|---|---|---|---|
| 1 | Цена для Польши, НДС, доставка, акции | Core **$449** разово, Premium **$548** за первый год, Premium + AI **$649** ([WGS](https://dantelabs.com/whole-genome-sequencing)). ⚠️ На [странице заказа](https://www.dantelabs.com/order) у планов написано «Then $99 a year» и «Then $200 a year». Цену в EUR/PLN и НДС увидеть не удалось: сайт пишет «price for your country is shown… at checkout», а checkout с `?country=PL` всё равно показывает US и $449. Неофициальная страница dante-rebuild.pages.dev называет «from €399» — **не подтверждено**. **FRIEND10 и акция Black Friday 2026 не подтверждены**: на сайте и в справке их нет. | **€329,99** с НДС, доставка бесплатная («Tax included. Free shipping») ([товар](https://shop.tellmegen.com/en/products/ultra-wgs-dna-kit)). В PL-магазине та же цена в EUR, цены в PLN нет. ❌ Не ~$299: в американском магазине [$329.99](https://shop.tellmegen.com/en-us/products/ultra-wgs-dna-kit). **Код BLACK15: −15% на Advanced и Ultra до 27.11** ([shop](https://shop.tellmegen.com/en/collections/ultra)), получается ≈ €280,49 (мой расчёт). ⚠️ На странице коллекции у товара метка «Sold Out / Wyprzedane», а на странице товара есть кнопка «Add to Cart». |
| 2 | Доставка в Польшу, бесплатный возврат | По сайту «Free delivery worldwide», «Pre-paid return label included» ([главная](https://dantelabs.com/)). Для ЕС отправка обычно FedEx в течение 24 ч, доставка 5–10 рабочих дней ([support](https://support.dantelabs.com/articles/shipping-and-kit-return), [сроки](https://support.dantelabs.com/articles/kit-not-arrived)). **Польша в явном списке стран не найдена** (списка нет вообще). | Пересылка в обе стороны включена в цену, но только если образец отправляют обратно из страны покупки ([Terms 10.2](https://shop.tellmegen.com/en/policies/terms-of-service), [Refund 9.2](https://shop.tellmegen.com/en/policies/refund-policy)). Есть польский сайт и офис: Bielany Wrocławskie, info.pol@tellmegen.com ([PL](https://www.tellmegen.com/pl/)). ⚠️ Исходное «free both ways worldwide» верно с оговоркой: покупка и возврат должны быть в одной стране. |
| 3 | Тип образца | Капля крови из пальца («finger-prick blood spot») ([WGS](https://dantelabs.com/whole-genome-sequencing)). ⚠️ В справке есть и [инструкция по слюне](https://support.dantelabs.com/articles/saliva-collection), в Terms написано «saliva or blood». | Слюна, 2 мазка и пробирка с консервантом ([Ultra](https://www.tellmegen.com/en/dna-test-ultra)). |
| 4 | Файлы, сборка генома, размеры | FASTQ, BAM, VCF ([WGS](https://dantelabs.com/whole-genome-sequencing)). CRAM и gVCF не упоминаются. Целевой объём 96 Gbp ([depth](https://support.dantelabs.com/articles/sequencing-depth)). Размеры: VCF «несколько сотен МБ», BAM около 50–90 ГБ, FASTQ около 100 ГБ ([raw-data](https://support.dantelabs.com/articles/raw-data)); в примере на главной BAM 98,4 ГБ и два fq.gz по 42–44 ГБ. ⚠️ **Сборка не ясна**: в примере на главной GRCh37, в описании Premium + AI «GRCh38 alignment». | ⚠️ Форматы описаны по-разному: на [странице Ultra](https://www.tellmegen.com/en/dna-test-ultra) «CRAM, CSV, FASTQ, VCF»; в [справке](https://help.tellmegen.com/faq/your-results/what-raw-data-formats-do-you-offer/) только «VCF and/or FASTQ»; в Terms 15.1 «VCF and, when offered, BAM or FASTQ». ❌/⚠️ Исходное «FASTQ + VCF, no BAM» в целом верно, но возможен CRAM. Сборка GRCh37: «same reference genome (GRCh37) in all products» ([tech](https://www.tellmegen.com/en/technology-and-laboratory)). Около 90 ГБ сырых данных, покрытие около 30x, при покрытии ниже 20x результат не публикуют. Лаборатории: Eurofins (Дания), GenePlanet (Словения), MGI (Польша); ⚠️ какая из них делает Ultra, не указано. Variant calling: DeepVariant. Пары R1/R2 и запрос ссылок по email известны только со слов пользователя у [DNAGenics](https://www.dnagenics.com/blog/downloading-fastq-files-from-tellmegen-ultra-30x-wgs-a-guide); официально **не подтверждено**. По [Trustpilot](https://www.trustpilot.com/review/tellmegen.com) (2026): фактическое покрытие 45x у двух пользователей; CRAM/CSV у одного пользователя сначала отсутствовали; в VCF нет rsID. |
| 5 | Срок хранения, плата, истечение ссылок | «Download… anytime», «lifetime Genome Manager access» ([WGS](https://dantelabs.com/whole-genome-sequencing)). Ссылки истекают через **7 дней**, их можно сгенерировать заново ([raw-data](https://support.dantelabs.com/articles/raw-data)). Платы за скачивание нет. ❌ **Правило «30 дней на скачивание» не найдено**: «30 дней» встречается только у срока удаления данных и возврата набора. Что будет с доступом к сырым данным без Premium, **не подтверждено** ([/membership](https://dantelabs.com/membership) отдаёт HTTP 500). | **Скачивание только при активной подписке tellmeGen+.** В Ultra включены 3 бесплатных месяца, дальше €29,99 в год. После окончания подписки есть 12 месяцев льготного периода, затем данные удаляются (резервные копии — в течение ещё 90 дней) ([tellmeGen+](https://www.tellmegen.com/en/tellmegen-plus), [Terms 14–15](https://shop.tellmegen.com/en/policies/terms-of-service), Privacy 9.2/9.4). Бесплатно 3 скачивания в год, дальше по €4,99. Срок действия ссылок **не подтверждён**. |
| 6 | Срок выполнения | Официально 6–8 недель ([WGS](https://dantelabs.com/whole-genome-sequencing)), по Terms до 8 недель, в справке «1–3 месяца» ([processing-time](https://support.dantelabs.com/articles/processing-time)). **По отзывам 2026 г.**: 12–20 недель и дольше, есть ожидание по 15 месяцев и даже с 2023–2024 гг. ([Trustpilot](https://www.trustpilot.com/review/dantelabs.com)). | Официально 4–6 недель после получения образца лабораторией ([FAQ](https://shop.tellmegen.com/en/pages/faq)). **По отзывам 2026 г.**: от 4–5 недель до 50 дней и около 10 недель; одному пользователю обещали 30 дней, вышло около 10 недель ([Trustpilot](https://www.trustpilot.com/review/tellmegen.com)). |
| 7 | Происхождение и родственники | Автосомное происхождение по 26 популяциям плюс Y/mt-гаплогруппы; на [странице WGS](https://dantelabs.com/whole-genome-sequencing) это указано без привязки к тарифу. ⚠️ В списке Core этого нет, а «Complete ancestry» перечислено в Premium + AI. **Входит ли в Core, не подтверждено.** Поиск родственников не найден. | Происхождение, материнская и отцовская линии (гаплогруппы), неандертальская ДНК ([Ultra](https://www.tellmegen.com/en/dna-test-ultra)). Поиск родственников DNA Connect «included in all our genetic tests». |
| 8 | Приватность | Оператор данных Dante Labs International Inc.; представитель в ЕС Dante Labs S.r.l. (L'Aquila, Италия); право Италии; GDPR; возможна передача за пределы ЕЭЗ по SCC ([privacy](https://dantelabs.com/privacy), [terms](https://dantelabs.com/terms)). Удаление данных в течение 30 дней, образец уничтожают по запросу ([delete-data](https://support.dantelabs.com/articles/delete-data)); ⚠️ в Privacy написано «sample destroyed right after results». Исследования только с отдельным согласием. Место хранения **не указано**. ⚠️ По PitchBook компанию купили 01.04.2026; [GenomeTesting.org](https://genometesting.org/blog/dante-labs-review.html) называет покупателя, Bio Cell Tech FZCO (ОАЭ), но это **не подтверждено**. | GENELINK, S.L. (Валенсия, Испания), право Испании ([Terms](https://shop.tellmegen.com/en/policies/terms-of-service)). «Genetic analysis and data storage take place entirely within the EEA» ([Privacy 12.1](https://shop.tellmegen.com/en/policies/privacy-policy)). Образец хранят 60–120 дней после результатов, не дольше 6 месяцев. Исследования только с отдельным отзываемым согласием. DPO: dpo@tellmegen.com. |
| 9 | Язык | Сайт на английском; справка на en/es/fr/it/de/ar ([support](https://support.dantelabs.com/)). | Английский есть (а также польский и ещё около 15 языков). Поддержка 24 часа в будни, на выходных 9:30–21:30 CET ([home](https://www.tellmegen.com/en/)). |
| 10 | Тревожные сигналы 2026 г. | Trustpilot **1,8/5** (4386 отзывов, 55% — 1★). Среди жалоб с октября 2026 г.: месяцы и годы без результатов, отказы в возврате денег, необходимость подписки для просмотра отчётов. Отдельный профиль [Danteomics](https://www.trustpilot.com/review/danteomics.com) 1,9/5: «новый портал не видит старый заказ». Смена владельца в 2026 г. | Trustpilot **3,7/5** (208 отзывов, 22% — 1★). Жалобы: превышение срока 4–6 недель, неполные или нестандартные файлы (не было CRAM/CSV, нет rsID), необходимость подписки, €119 за повторный набор для слюны, шаблонные ответы поддержки ([Trustpilot](https://www.trustpilot.com/review/tellmegen.com)). При этом есть положительные отзывы о качестве FASTQ. |
| 11 | Dante: апгрейд Core → Premium без нового образца | **Не подтверждено.** Страница [/upgrade](https://dantelabs.com/upgrade) рассчитана на загрузку данных 23andMe и т. п. Справка: подписку можно отменить и возобновить в Genome Manager, после отмены доступ к отчётам уровня Premium пропадает ([refund-policy](https://support.dantelabs.com/articles/refund-policy)). | — |

### Возврат денег (дополнительно)
- **Dante.** По [return-policy](https://dantelabs.com/return-policy): возврат только в течение 14 дней, пока образец не получен лабораторией, со сборами €25 + €10, плюс ещё €35, если образец уже в пути. ⚠️ Это расходится со [справкой](https://support.dantelabs.com/articles/refund-policy), где обещан возврат за неиспользованный набор в течение 30 дней.
- **tellmeGen.** 14 дней на отказ; вскрытый набор вернуть нельзя ([Refund](https://shop.tellmegen.com/en/policies/refund-policy)).

## Рекомендация

**Заказывать tellmeGen Ultra** (тариф один) с кодом **BLACK15 до 27.11** (≈ €280).
- Компания из ЕС; данные хранятся в ЕЭЗ; обратная доставка из страны покупки бесплатна.
- Отзывы 2026 г. в среднем заметно лучше, а задержки измеряются неделями, а не годами.
- Минусы: сборка GRCh37; нет BAM (будет FASTQ, может быть CRAM; BAM для GRCh38 соберёте сами из FASTQ); скачивание привязано к подписке.
- Порядок действий: сразу после выхода результатов, в течение 3 бесплатных месяцев tellmeGen+, скачайте FASTQ R1/R2, VCF и CRAM. Сверьте контрольные суммы, сделайте две копии (около 90 ГБ), после этого подписку можно не продлевать.

**Dante Labs не рекомендую.** По условиям всё выглядит хорошо: FASTQ, BAM и VCF без доплат, ссылки можно перевыпускать. Но в отзывах 2026 г. массово описаны многомесячные и многолетние задержки и отказы в возврате, в 2026 г. сменился владелец, а цены в EUR и условия для Польши подтвердить не удалось. Если всё же брать Dante, то только **Core** ($449): Premium нужен ради отчётов, для сырых данных он не нужен.

## Вопросы в поддержку

### tellmeGen (info@tellmegen.com, по Польше: info.pol@tellmegen.com)
1. Ultra сейчас в наличии? В EU-магазине на странице коллекции стоит «Sold Out».
2. Какие именно файлы будут: FASTQ R1/R2, CRAM, BAM, VCF (gVCF?) — и какая сборка у CRAM/VCF?
3. Скачивание по прямой ссылке или по email? Сколько действует ссылка?
4. Где секвенируют Ultra (Eurofins / GenePlanet / MGI) и на каком приборе?
5. Если заказать через EU/PL-магазин с доставкой в Польшу, обратная пересылка из Польши бесплатна?
6. Работает ли BLACK15 для доставки в Польшу?

```
Subject: Ultra WGS (30x) – questions before ordering (shipping to Poland)

Hello,

I am in Warsaw, Poland, and plan to order Ultra WGS (30x) with code BLACK15. I need raw data only. Could you please confirm:
1. Is Ultra in stock? The EU shop collection page shows "Sold Out".
2. Exactly which files I will receive (FASTQ R1/R2, CRAM, BAM, VCF/gVCF), and the reference build (GRCh37 or GRCh38).
3. How FASTQ is delivered (direct download or links by email) and how long the links stay valid.
4. Which laboratory and sequencer process Ultra samples.
5. That return shipping of the sample from Poland is free when ordering from the EU/PL shop.
6. That BLACK15 applies to orders shipped to Poland.

Thank you,
[Name]
```

### Dante Labs (hello@dantelabs.com)
1. Цена Core в EUR для Польши (с НДС и доставкой), работает ли FRIEND10 и есть ли акция Black Friday.
2. Отправляют ли набор в Польшу и есть ли предоплаченная этикетка из Польши.
3. Кровь или слюна; в какой лаборатории секвенируют.
4. Сборка генома для BAM/VCF у Core (GRCh37 или GRCh38), есть ли CRAM/gVCF.
5. Остаются ли сырые данные доступными бессрочно на Core без Premium.
6. Можно ли позже перейти с Core на Premium без нового образца и сколько это стоит.
7. Входят ли в Core происхождение и гаплогруппы.
8. Какие сейчас реальные сроки; кто владелец компании после смены в 2026 г.; где хранятся данные.

```
Subject: Core WGS – questions before ordering (shipping to Poland)

Hello,

I am in Warsaw, Poland, and want the Core 30x WGS kit for raw data only. Before ordering, could you please confirm:
1. The final Core price in EUR for Poland, including VAT and shipping, and whether code FRIEND10 or any Black Friday offer applies.
2. That the kit ships to Poland with a prepaid return label usable from Poland.
3. The sample type (blood spot or saliva) and the sequencing laboratory.
4. The reference build of the delivered BAM/VCF (GRCh37 or GRCh38), and whether CRAM or gVCF are available.
5. That FASTQ, BAM and VCF stay downloadable indefinitely with Core only, with no Premium subscription and no fees.
6. Whether Core can later be upgraded to Premium without a new sample, and the price.
7. Whether ancestry and Y/mt haplogroups are included in Core.
8. Current real turnaround time, the legal owner of the company after the 2026 ownership change, and where genetic data is stored.

Thank you,
[Name]
```
