# BA audit — Calendar simplification

**ผล:** พร้อม HRM ตรวจแล้วส่ง TRI; source-format migration **ยังไม่ applied**. Live contract/template เปลี่ยน comments เท่านั้น; generator, tests, config, workflows, deployment และ HRM logs ไม่เปลี่ยน. T-53 manual acceptance ถูกยกเลิกตาม H-119 ไม่ใช่ manual PASS และไม่สร้างงานทดสอบเดิมกลับมา

## 1. Evidence / method

- อ่าน H-119, repo BA prompt, current source/schema/contracts/tests, backupเต็ม 1518 lines และ sibling Medallion แบบ read-only. ตรวจ hash backupก่อน rewriteและหลังจบ
- Backup: `DocsForAgent/archive/draft_reviewd_by_agent_v2.pre-calendar-simplification.20261005T162512Z.md`; SHA-256 `4f07413bed046968e77a758c322750a03f9cf5a097afb264f9219314f34be712`; 279117 bytes / 1518 lines
- `audit_inputs.py` รันผ่าน `uv run python`: ตรวจ ODCS pinned schema, parsed contracts, current calendar, counterexample probes, AST function counts, per-key lexical traces. ผลจริงอยู่ `audit-inputs.json`; lexical hit ไม่ถือเป็น consumer จนอ่าน caller/semantics
- Repo siblingจริงอยู่ `../../Medallion/` จาก repository root (H-119 ใช้ชื่อ siblingแบบย่อ); ไม่แก้ sibling. `config_requirements.md` เป็นคำขอเก่าที่ยังบอก “ไม่มีrecovery/v3/privacy” จึงใช้เป็น **purpose/backlog** ไม่ใช้เป็น current delivery proof. Actual sourceและ H-118/H-119 ชนะคำบอก gap เก่า
- Current public/deployment state อ้าง H-118/H-119/STATE เท่านั้น ไม่ remote-query/deploy ใน BA. U2Mส่งจริง; auto OIDC uploadไม่ได้verified; manual cancelled

## 2. What is actually authored and consumed

cc.customer / cc.credit_card / cc.credit_card_txn: frequency daily, latency4h, recovery2d จริง. Owner cutoff/timezone/dayoffset/schedule **ไม่มี**. Actual compiled calendarทั้ง3 = PENDING_OWNER; derived seconds14400/172800; optional arrays[]; scalarsที่ownerยังไม่ให้null. Templateเดิมไม่มีrecoveryด้วย

### Common whole-object trace (ไม่ใช่ deployed business use)

- `src/mdf/validation.py:235–253` เรียก `read_calendar`, missing→warning/errors→CALENDAR_INVALID; static format check
- `src/mdf/compile.py:208,240` ใส่ `compiled_calendar` ลงทั้ง2 layers; **producer** ไม่ได้คำนวณ arrival
- `src/mdf/diff.py:227–239` เทียบ **whole object** เพื่อ calendar_changed/review ไม่ได้แปล scheduleรายkey
- `src/mdf/package.py:147–158,326–328` missing-list→release pending warning; ไม่ใช่ business date scheduler
- `.github/workflows/release.yml:121–133,162–164,183–185` อ่าน compiled `calendar.status` จริงเพื่อรายชื่อpendingในnotes/summary; **status reporting consumer** ที่พบใน code. H-118 มีexecutionlogไม่ใช่การเปิด renderedsummaryใน BA
- `tests/test_calendar.py:155,181,194,206,226` มี static-validation/compile/owner-pending tests; `tests/test_manifest_release.py:231` มี pending release-gate test. Testsไม่ใช่ deployed runtime consumer
- `../../Medallion/framework/_shared_helpers_bronze.py:275–297` `resolve_business_date` อ่าน **legacy ODCS** frequency/latency/expected_at/timezone; ออก `execution: PLAN_ONLY`. Line290 hardcodes `late_recovery_window_days:2`; **ไม่ได้อ่าน recovery_window_secondsจากoutput**. `framework/bronze_cc.py` เรียก helperเพื่อ plan. ไม่พบcalendar-normalized businessconsumerใน sibling `.py` ที่ตรวจ; ไม่อ้างว่าไม่มีconsumerทุกระบบในโลก
- generic package/hash/registry copiesรักษาcalendar bytes แต่ไม่ตีความeachfield. Common whole-object traceใช้กับทุกoutputkeyด้านล่าง; row “ไม่มี” หมายถึงไม่มี **field-level normalized business reader** ใน reposที่ตรวจ

### Every current calendar key — source / trace / recommendation

| Output key | Current source → producer (`src/mdf/calendar.py`) | Actual field-level consumer / business purpose | Recommendation / compatibility |
|---|---|---|---|
| status | missing list from read_calendar:314–345 → line400 | release.yml:131อ่านตรง; pending owner reporting | **keep derived output**, ไม่ownerinput. ต้องstatuscompleteเฉพาะvalid input; ไม่ลบrelease warning |
| schedule_type | customProperties.business_schedule.type → 279,401 | ไม่พบnormalizedbusinessreader; Phase3เลือกbusiness-date eligibility | **keep core input/output**; unknownnull ไม่อนุมานจากfrequency. preserve5types |
| timezone | customProperties.timezone → 76–93,402 | siblinglegacyODCS282/294เช็คopenfield PLAN_ONLY; Phase3localexpectedinstant | **keep core**; ownernull. Staticstringnonemptyonly; noIANAdep. sourcecutoverต้องcoord sibling |
| expected_at | slaProperties.expected_at → 96–113,403 | siblinglegacy280/294 PLAN_ONLY; cutoff+latency missinginstant Phase3 | **keep core** ownerHH:MM/null; nofake02:00default |
| expected_day_offset | customProperties.expected_day_offset → 116–132,404 | ไม่พบ; Phase3deliverydayrelativebusiness_date | **keep core** int>=0/null; boolinvalid; notderivefromclock |
| effective_from | business_schedule.effective_from → 201–209,405 | ไม่พบ; Phase3versionedscheduleeligibilitystart | **keep core when schedule chosen**, unknownnullpendingในnewmodel ไม่สร้างวันเริ่มจริง |
| effective_to | business_schedule.effective_to → 210–228,406 | ไม่พบ; Phase3scheduleend | **optional** input; absent/null=noendrestriction; keepoutputkeynull |
| holidays | business_schedule.holidays → 164–187,285,407 | ไม่พบ; Phase3workday_excluding_holidays | **optional/conditional**; ต้องownerlistเมื่อexcludeholidaysและownerยังไม่รู้ไม่defaultcomplete. Omittedunused→output[]; providedmalformedmusterror |
| explicit_dates | business_schedule.explicit_dates → 286–296,408 | ไม่พบ; Phase3explicit schedule | **conditional** nonemptyถ้าscheduleexplicit_dates; otherstypeomit→[]; sort/duplicatesguardkeep |
| exceptions | business_schedule.exceptions passthrough → 308,409 | ไม่พบ; ไม่มีvalidatedshape/precedence; generic objectdiff/hashเท่านั้น | **defer nonempty authoring** จนOQ-CS-1ตอบ; keepcompatibilityoutput[]; ไม่inventaction/dateclass |
| day_of_month | business_schedule.day_of_month → 231–250,298,410 | ไม่พบ; Phase3monthlyeligibility | **conditional** inputwhenmonthly, int1–31; keepoutputnullotherwise |
| day_of_month_policy | business_schedule.day_of_month_policy → 252–258,299,411 | ไม่พบ; Phase3handlingunsuitableday; currentcodechecksเพียงtruthiness | **conditional / defer enum semantics**; ห้ามcopyexample last_business_dayเป็นbusinessapproval; keepoutputkey |
| missing_after_seconds | slaProperties.latency{value,unit} → 57–73,326–329,412 | ไม่พบnormalizedreader; sibling277–289ใช้legacylatencyในplan; Phase3expectedinstant+latency | **keep derived**, removeจากauthorinput. known4h→14400; nevercomputearrivalfromwallclock |
| recovery_window_seconds | slaProperties.recovery_window → 135–161,413 | ไม่พบnormalizedreader; sibling290hardcoded2dไม่countconsumer; Phase3stopautopoll | **keep derived**, removeจากauthorinput. known2d→172800; recoverwithinwindowยังdateorderguard |
| frequency | slaProperties.frequency → 396–397,414 | siblinglegacy277/286 PLAN_ONLY; SLAcadencelabel | **keep input/output forcompatibility**, sourceblockเดียว; ไม่ใช้แทนschedule_type/noautofill |

15 keys audited. “ยังไม่มีbusinessconsumer” ไม่เท่ากับ “ไร้ประโยชน์ลบทิ้งได้”: scopeรอบ12เคยอนุมัติoutputและPhase3purposeแล้ว. ลดmandatoryauthoring/duplicatedguardsโดยไม่breakinginterface. Physicalremove/deprecateoutputใดต้องuserapproval+versionplanใหม่

## 3. Generator complexity: simplify the path, not the guarantees

AST evidence: `calendar.py` 415lines / 17 top-level functions. ตัวhelper `custom_property`/`has_custom_property` เป็นsharedreaderที่privacy/readerใช้ด้วย ไม่ใช่calendar-only codeทิ้งได้ทั้งหมด. `read_calendar`32lines, `compiled_calendar`41lines; typedvalidatorsแยก10+helpers. จำนวนlinesรวมcommentsไม่ใช่proofว่าoverengineeringทุกfunction

**ความซับซ้อนจริง:** sourceกระจาย SLA+customProperties+business_schedule, entrylookupซ้ำและแยกmissing sentinelจากnull; read/normalizeถูกเรียกซ้ำในvalidate, compile, diff, pending-summary. Mappingnestedsource→flatoutputทำให้เปลี่ยนcontract1จุดต้องรู้หลายfunction. Coreparserเป็นsingleplaceอยู่แล้ว: ไม่ได้มี5parserที่ควรสร้างregistryมาครอบอีก

| Class of check | Keep / simplify | Reason |
|---|---|---|
| Absent scalar vs explicitnullowner | **simplify new-source read** `get`→None; missing/nullunconfigured | Currentlegacynull→malformedไม่เหมาะauthoring; migrationต้องเปลี่ยนreaderไม่ใส่nullliveก่อน |
| Lookup `_sla_entry` / `_custom_value`กระจาย + nested `business_schedule` | **one new source block**; legacyprojectionเล็กเฉพาะmigration/diff | ไม่ต้องlayeradapterframework/cache/typedconfigclass; ไม่claimperformanceproblemของ3datasets |
| Sourceformat/types/time/date/int/range/duplicate/unit | **keep atvalidate boundary** ไม่duplicatecompiledcaller | missing=nullไม่ใช่ให้ผิดรูปแบบผ่าน; boolไม่ใช่int, nonemptytimezonestringตามuser |
| Durationconversion / deterministicdatesort / status | **keep one small normalization** | Seconds/statusderivedไม่input; conversionsจำเป็น compatibilityoutput |
| Cross-fieldrecover>=latency / conditionalmonthly/explicitdates | **keep scoped tousedtype** | ไม่บังคับdailyกรอกทุกpolicy; wrongprovidedvalueต้องerror |
| IANAlookup/tzdata/allowlist | **do not add** | Userdecisionชัดเจนและcross-platformdeterminism |
| Calendar guardsในcompiledhelperเมื่อcallerผ่านvalidateแล้ว | **do not revalidate all output** | Compilerboundaryvalidatesก่อนอยู่แล้ว; แต่อย่าใช้helperresultจากinvalidinputเป็นCOMPLETEproof |
| Package/identity/hash/path/zip/PCI/breakingversionguards | **retain independent trust boundaries** | ตรวจคนละartifact/threat ไม่ใช่redundantcalendarfieldguards |

**Smallest proposed path:** ODCS `customProperties` array lookup `calendar`หนึ่งครั้ง → validate sourceครั้งเดียว → `.get(key)` สำหรับscalar → normalize durations/status/listในhelperเดียว → compile/diff/pendingusehelperเดียว. อย่ากระจายget/shapeในทุกcaller. Currentwholeobjectdiffคงเป็นreview; newvslegacyequivalentไม่แจ้งเปลี่ยนเพราะauthoringrepresentationเฉย ๆ

### Actual counterexamples (probe only, no code changes)

1. Root `calendar` fails pinned ODCS: `additionalProperties:false`, “calendar unexpected”. `customProperties[property=calendar].value`objectผ่านschema แต่ **currentreaderไม่อ่าน**; stagedsource-onlyจะปล่อยfrequency/latency/recoveryเป็นnullในoutput แม้validatewarnแล้วผ่าน. ดังนั้น schemaPASS **ไม่ใช่generatorcompatibility**
2. Legacyowner explicitnullผ่านODCSแต่ `read_calendar`ให้4errorsและmissing=[]; direct `compiled_calendar`ออกCOMPLETEเพราะดูmissingไม่ดูerrors. Compilerจริงvalidateก่อนเขียนจึงไม่claimว่า productioncompileรับinvalidแล้ว; diff.pyไม่มีvalidatecallerที่พบ จึงต้องTRIระบุvalidbaseline/currentcontractpreconditionให้ชัด ไม่เติมguardsทุกcallerโดยไม่จำเป็น
3. Wrong holidays scalar→silently[] (`_check_date_list:168–169`) no calendarerror; exceptions `["not-a-date"]`ส่งผ่านไม่validate (`308`). Negative latency−4h→−14400 no calendarerror. เป็นvalidationgapsที่ควรแก้ในการcoordinatedboundarychange ไม่ใช่เหตุผลเพิ่มframework. NewFR-N.5 requires provided malformed values to error; negative/non-finite durationshouldrejectในnewmigrationregression; legacybehaviorยังไม่แก้รอบนี้

## 4. Applied authoring vs staged migration

**Applied:** comments blockที่มีproposedcalendarone-objectในTemplate+3cc. ค่าจริงfreq/latency/recoverycopied; ownernull. Templateถอน02:00ตัวอย่างที่อาจถูกเข้าใจว่าdefault;แก้stalerule/envpathsและdurationunitcommentให้ตรงcurrentparser; ccแก้pipelinepathcomment. YAMLparsedpayloadและREALITYlinesทุกไฟล์ unchanged (byte-line hashesตรวจจริง)

**Staged:** `proposed/DataContract/...` full4ODCSและ SAMPLEfragment. ใช้rootpropertiesเดิม/customPropertiescalendarobject, ไม่มีlegacycalendarSLAหรือcustomcalendarfieldsเหลือ; sourceoneblock, unknownownernull. Stageคงnon-calendarpayloadและREALITYlines. ทั้ง4ODCSผ่านpinnedschemaแต่ไม่activate/move/discoverในlivepath. Currentparserreadslegacyonly — stageไม่readycompileด้วยรุ่นปัจจุบัน. SAMPLEdates/time/timezoneไม่ownerconfirmation; fictionaltimezoneใช้แสดงstring-onlycheck ไม่runtimevalid

**Cutoverเดียวผ่านSWE:** reader/validator/sourceprojection + unchangedoutputmapping + Template/3ccsourceconversion + focusedcompatibilitytests/docs. ไม่ต้องschema/dependency/frameworkเพิ่ม. Newsourceกับlegacysourceที่อยู่พร้อมกันต้องerror ไม่preferเงียบ ๆ; fallbacklegacyreadไว้ใช้diff/oldcontractinspectionเท่านั้น. Unknownownernull→warning; conditionalmissingownerinputs→pending; malformednon-null→error. Frequencylabelไม่autoapprovebusinessschedule. Reportนี้เสนอmigration ไม่อนุมัติimplementationหรือproductionrelease

Versionplan: ODCSapiVersionv3.0.2ไม่เปลี่ยน; manifestยังv3เพราะartifactlayoutเดิม; **ถ้าoutputschema/semanticsเปลี่ยนต้องversionmigrationเพิ่มก่อน**. Contractversionเป็นbusiness/schemaidentity ไม่ใช่sourceformatselector. ยังไม่bumpcontractversionในBA; sourceonlyeditพิจารณาmetadata-only/semverruleตามFR-Eก่อนSWE. Oldreleasebytes/Volumeuntouched

## 5. SSOT reduction / preservation

Live SSOTเป็นoperationalrequirementsใต้30KB ไม่ใช่roundhistory. Originalfullอยู่archiveเท่านั้น; active detailอยู่ `active-obligations.md` แบบID-addressable เปิดเฉพาะneededIDs. Currentdecisionsย่อให้operativeconstraints ไม่copyappendixchronology. Dataentities/securityที่ไม่มีIDก็retainแยก ไม่ใช้IDcensusเป็นข้ออ้างทิ้งเนื้อหา

`build_coverage.py` census **all explicit old IDs** และseparatedefinitionlocations ไม่นับเพียงreferenceในliveเป็นretention. Mapactionunique, source-lines, targetanchor, activeflag; FR/NFR/AC/DQ/BR/DPR/BF/backlog/risk/openquestions/phase3tasks/condensedcurrentdecisionsretainหรือrelocate. CanceledACsexplicit supersede; completedtasks/closedquestions/citationonlyarchive. Rangeabbreviationไม่สร้างfakeidentifier; originalactualdefinitionsตรวจครบ

Effectiveprecedenceในactive-detailแก้ stale clauses: newmanifestv2→v3, unknownv3→unknownv4, flatnew→per-source, looseassets→zip, typedtimezoneonly, resolvedauthority, pendingowner, PIImaskdefer, olderdateblock/humanbackfill และmanualcancellation. Oldverifier/lineage/security/releaseversion/determinismguaranteesคงเดิม. BacklogPhase3/4ไม่labeldeployed

Machineverificationใช้ `verify_ba.py` + `verification.json`: backuphash, counts+exactanchors, fence/headings/tablelinks, schema, parsedpayload/REALITY, stagedsingle-source, scope/noimplementationchanges. Actual `uv run mdf validate` transcript `validate.txt`; nofullsuite. Metricsและscopeledgerท้ายreportสร้างจากfilesystemจริง ไม่ประมาณด้วยสายตา

## 6. TRI input / smallest ticket proposal (not ticket creation)

**Input order:** H-119 → compactSSOT → H-120 → auditsections2–4 + sourceevidenceเมื่อต้องใช้ → active-obligationIDsที่เกี่ยวข้อง. ไม่loadfullbackupอัตโนมัติในTRI; HRMตรวจbackup/coverageก่อน

**1 coordinated SWE ticket proposal:** nullable singlecalendar source-reader + boundaryvalidation + sameoutputmapping + cutover4ODCS + focusedtests/docs. Scopeไม่deploy/publish, nofullsuiteโดยdefault, noTRIspawnโดยBA. MEDALLION consumerchangeเป็นPhase3dependencyแยกโดยownerrepoนั้น ไม่ลักลอบแก้siblingในticketgenerator

Acceptance: AC-59…65 + currentAC-52…57; readers/privacy/manifestcompatibility AC-46…49/51 regression โดยมีv3override; boundarynegativeinput/null/dual-source/sortedlists/conditionalfields; outputbyteparitybronze/silver andnew-vslegacyfixture; oldreleasev1warn/v2/v3verify; unknownversion/tamper/hash/path/lineagemismatchstillfail. Deliveryartifactstaticchecksไม่เท่ากับmanualre-execution. ไม่มีQA/user/HRMsignoffแทนผู้มีสิทธิ์

### Open decisions / severity / owner

- **No P0 blocking BA/TRI for staged migration.** Newmodel/outputversion/sourcecollisionpolicyต้องTRIยืนยันก่อนSWEdispatch; ถ้าต้องเปลี่ยนoutputหรือdropcapabilityกลับผู้ใช้ก่อน ไม่อนุมัติเอง
- **P1 OQ-P5-10 / sourceowner:** realHH:MM,timezone,offset,schedule/effectivefromและconditionaldates/policy; recovery2dexistingยังขอbusinessconfirm. ไม่blockpendingflow แต่blockruntimearrival
- **P1 OQ-CS-1 / BA+runtimeowner:** exceptionsrecord/action/dateprecedence+daypolicyenum. Defernonemptyexceptions; phase3capabilityจะenableเป็นP0จนชี้ขาด
- **P1 OQ-CS-2 / Medallionowner:** legacyODCS PLAN_ONLYยังไม่usev3resolvedauthority; no normalizedbusinessconsumerverified; ต้องcoordinatemigrationก่อนproductionruntime
- **Phase3 P0 before respective runtime implementation:** OQ-P1-22 mastermissingfact/gold; OQ-P1-23 dataFKdefecthandling; do not inventunknownmember/quarantinepolicy. Confirmedblock+humanbackfillคงเดิม, cascadewithinhumanrangestillclarify
- **Goldreserveddepth:** old wording2levelsและinterpretation3pathsegmentsไม่เท่ากัน; clarificationก่อนenablePhase3 ไม่แก้currentv3two-segmentverifierให้goldเอง

HRM next: verifyH120/artifacts then sequentialTRIdispatch. BAจบที่handoff ไม่สร้างticket/agent/deployment

## 7. Verified metrics / file ledger

- Original279117bytes/1518lines → live24220bytes/121lines; ลด91.32%. BackupSHA-256ตรงค่าด้านบน ไม่เปลี่ยน
- 526explicitoldIDs: retain19 / relocate400 / supersede7 / archive100. Activeobligations419; activearchive0. รายละเอียดsource/targetทุกIDอยู่map ไม่ถือcountsเป็นproofbusinesspolicyด้วยตัวเอง
- Actualvalidationexit0, errors0, warnings3(`CALENDAR_PENDING_OWNER`), finalBAchecksPASS. Liveและstaged4contractsทุกไฟล์pinnedODCSPASS; liveparsedpayloadตรงHEADและcalendaroutputไม่เปลี่ยน; REALITYlinesตรงoriginalทุกไฟล์
- Modifiedfiles: compactSSOT + START_HERE + Template/3cccomments. CreatedIDmap, active-detail, analysis, H120, audit/coverage/verificationhelpers/evidence, staged4contracts+SAMPLE. Exactpathsอยู่verification.json
- **Git visibility:** `.gitignore:11` ignoresDocsForAgent/, `.gitignore:14` ignoreshandoffs/. จึงมีเพียง4trackedcontractdiffsและnewreportsในgitstatus; ignoredSSOT/H120ถูกเขียนและตรวจจากfilesystemจริง ไม่ใช้gitdiffเป็นevidenceเพียงอย่างเดียว. ไม่แก้ignoreหรือforce-add
- Non-BAuntracked `qa-evidence/E6/T053/` คงเดิม. No src/tests/config/workflow/git-write/deploy/fullsuite/HRMlogchanges. Pathrestrictionใช้PythonจากC:/Users/Userแล้วexactnativecwd; uvwarningไม่ทำให้exitfail
