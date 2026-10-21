# Industry playbooks — Egyptian B2B software/automation prospects

Each playbook is a research hypothesis generator, not a claim that every company in the sector has these problems. Use it to decide which queries to run and what to look for; confirm everything else in discovery.

For every playbook: `evidence_to_look_for` are things you can actually observe publicly (website pages, Maps categories, job postings). `disqualifiers` mean drop the lead or mark it low-confidence even if it matched the search query.

## 1. Manufacturing & industrial
- **AR queries:** مصانع مواد غذائية, مصانع بلاستيك, مصانع أثاث, مصانع مواد بناء, مصنع قطع غيار صناعية
- **EN queries:** food manufacturers, plastics manufacturer, furniture factory, building materials manufacturer, industrial spare parts
- **Evidence to look for:** multiple product lines/catalog pages, "فروع"/"مصانع" (plural) in About pages, ISO/quality-certification pages (implies process maturity worth integrating), a careers page listing "مدير إنتاج", "مهندس صناعي", "ERP", "IT".
- **Opportunity hypotheses:** production/inventory tracking, multi-warehouse stock visibility, QC/batch record digitization.
- **Decision-maker role:** Operations Director, Plant Manager, IT Manager.
- **Disqualifiers:** single-product micro-workshop, no evidence of >1 location or >~20 staff.

## 2. Wholesale & distribution
- **AR queries:** شركات توزيع مواد غذائية, موزعين أدوية, توزيع قطع غيار سيارات, شركة توزيع FMCG
- **EN queries:** FMCG distributor, pharmaceutical distributor, auto parts wholesaler, food distribution company
- **Evidence to look for:** "مناديب مبيعات"/sales-rep language, dealer/distributor-login pages, multiple branch addresses, a product catalog PDF instead of a searchable site.
- **Opportunity hypotheses:** order management, sales-rep route/visit tracking, purchase-order to warehouse integration.
- **Decision-maker role:** Sales Operations Manager, General Manager, Supply Chain Manager.
- **Disqualifiers:** single-location retail shop misclassified as "distributor" by Maps category.

## 3. Logistics, freight & warehousing
- **AR queries:** شركات شحن ولوجستيات, شركة نقل بضائع, مخازن تخزين, شركة توصيل
- **EN queries:** freight logistics company, warehousing provider, fleet operator, last-mile delivery Egypt
- **Evidence to look for:** fleet-size claims, "تتبع الشحنة"/shipment-tracking language (may already have software — check if it's third-party or custom), multiple warehouse addresses.
- **Opportunity hypotheses:** driver/dispatch coordination, real-time shipment visibility, customer delivery-status portal.
- **Decision-maker role:** Operations Manager, Fleet Manager, IT/Systems lead.
- **Disqualifiers:** a single-van courier with no fleet/warehouse evidence.

## 4. Field service & maintenance
- **AR queries:** شركة صيانة معدات صناعية, صيانة تكييفات مركزية, صيانة مصاعد, شركة صيانة عامة
- **EN queries:** industrial maintenance company, HVAC maintenance, elevator servicing, equipment maintenance Egypt
- **Evidence to look for:** "فريق فني"/technician-team language, service-contract/SLA mentions, coverage-area lists implying dispatch complexity.
- **Opportunity hypotheses:** work-order/dispatch system, technician mobile app, SLA/contract tracking.
- **Decision-maker role:** Operations Manager, Service Manager.
- **Disqualifiers:** one-person handyman service.

## 5. Food production & distribution
- Subset of (1) and (2) — use both query sets; look additionally for HACCP/food-safety certification pages (implies process documentation already exists, a good integration hook) and cold-chain/refrigerated-fleet language.

## 6. Pharmaceutical & medical-supply distribution
- **AR queries:** شركة توزيع أدوية, مستلزمات طبية بالجملة
- **EN queries:** pharmaceutical distributor Egypt, medical supplies wholesaler
- **Evidence to look for:** EDA/regulatory registration mentions, cold-chain language, multi-branch pharmacy-chain relationships.
- **Opportunity hypotheses:** batch/expiry tracking, pharmacy order portal, regulatory reporting automation.
- **Decision-maker role:** Operations/Regulatory Manager.
- **Disqualifiers:** single retail pharmacy (not a distributor).

## 7. Import/export & trading
- **AR queries:** شركة استيراد وتصدير, شركة تجارة عامة
- **EN queries:** import export company Egypt, trading company Egypt
- **Evidence to look for:** customs/freight-forwarding language, multiple supplier-country mentions, LC/trade-finance references.
- **Opportunity hypotheses:** shipment/documentation tracking, supplier-order integration.
- **Decision-maker role:** General Manager, Trade Operations Manager.
- **Disqualifiers:** personal/informal trading with no company site or registration evidence.

## 8. Multi-branch service businesses
- Any sector (clinics, gyms, education centers, retail chains) **once 3+ branches are confirmed** via Maps or an official branch-locator page.
- **Opportunity hypotheses:** central booking/scheduling, cross-branch inventory or customer records, franchise reporting dashboard.
- **Decision-maker role:** Operations Director, Franchise Manager.
- **Disqualifiers:** "branches" language that's actually just service-area marketing copy with one real address.

## 9. Construction suppliers & building-material distributors
- **AR queries:** شركة توريد مواد بناء, موزع مواد بناء, شركة مقاولات توريدات
- **EN queries:** building materials supplier Egypt, construction materials distributor
- **Evidence to look for:** project-reference pages (implies B2B contract work, not retail), bulk-quote-request language.
- **Opportunity hypotheses:** quote/tender management, project-based delivery scheduling.
- **Decision-maker role:** Commercial Manager, Operations Manager.
- **Disqualifiers:** small retail building-materials shop.

## Generic discovery questions (adapt per playbook)
1. إزاي بتتابعوا حركة المخزون/الطلبات دلوقتي — إكسيل، نظام جاهز، ولا شغل يدوي؟
2. لو عندكم أكتر من فرع/مخزن، إزاي بتشوفوا الصورة الكاملة لكل حاجة في مكان واحد؟
3. فيه حاجة بتتكرر يدويًا كل يوم أو كل أسبوع ممكن تتعمل تلقائي؟
4. العميل أو المورد بيتواصل معاكم إزاي لطلب عرض سعر أو متابعة طلب — فيه حد بياخد وقت كبير في ده؟
5. لو حد جديد دخل الفريق، هياخد وقت قد إيه لحد ما يفهم السيستم الحالي؟
