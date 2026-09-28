# ส่งคอนฟิกจาก GitHub สู่ Databricks Free Edition

**คำตอบ ณ 26 กันยายน 2026:** เส้นทางที่มีหลักฐานรองรับมากที่สุดคือให้ GitHub Actions สร้างและตรวจ **config release package** ของ commit ที่อนุมัติ แล้วให้ผู้ดูแลดาวน์โหลด artifact ของ run ที่สำเร็จ ตรวจ `manifest.json` ในเครื่อง ลงชื่อเข้า Databricks CLI ด้วย OAuth แบบผู้ใช้เมื่อ workspace รองรับ อัปโหลดไฟล์ไปยัง Unity Catalog Volume แยกโฟลเดอร์ตาม `release_id` และเรียก saved serverless Job ด้วย `job_parameters.release_id` หลังตรวจไฟล์ปลายทางครบถ้วนแล้ว. เอกสาร Free Edition ล่าสุดยืนยันว่า workspace มี Unity Catalog, ใช้ serverless compute และมีเพดาน **5 job tasks ที่ทำงานพร้อมกันต่อ account**; เอกสาร CLI ทั่วไปยืนยันคำสั่ง Volume และ Jobs แต่ **ยังไม่มีเอกสารทางการที่สาธิต OAuth/CLI upload เข้า Free Edition โดยตรง** จึงต้องทดสอบกับ account จริงก่อนถือว่าใช้งานได้. หาก OAuth หรือ CLI upload ใช้ไม่ได้ ผู้ดูแลยังมีเส้นทาง UI สำหรับอัปโหลดไฟล์เข้า Volume ที่ tutorial ของ Free Edition สาธิตไว้. โฟลเดอร์ release นี้ประกอบด้วย resolved JSON และ manifest; **ไม่ใช่ wheel** และยังไม่มีตัวรัน ingestion ใน repository. ต้องเตรียม notebook หรือ Python script ที่อ่านคอนฟิกแยกต่างหากก่อน Job จะประมวลผลจริง. Release แบบ tag ยังไม่ควรเป็นจุดรับมอบหลัก เพราะ `publish` job ปัจจุบันเรียก `uv` บน runner ใหม่โดยไม่ได้ติดตั้ง `uv` หรือ sync dependencies. ([ข้อจำกัด Free Edition; ปรับปรุง 25 ก.ย. 2026](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)) ([tutorial ของ Free Edition; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/getting-started/dataframes)) ([workflow ใน repository; ตรวจ 26 ก.ย. 2026](../.github/workflows/release.yml))

## หลักฐานหกเดือนล่าสุดรองรับเส้นทางแบบผู้ดูแล แต่ยังไม่รับรองทุก API ใน Free Edition

ช่วงเวลาหลักฐานที่ใช้ตัดสินคือ **26 มีนาคม–26 กันยายน 2026**. Databricks ระบุโดยตรงว่า Free Edition มี Unity Catalog เปิดไว้, ผู้ใช้เข้าถึง workspace catalog และ schema `default` โดยปริยาย และ tutorial ให้สร้าง Volume ด้วย `CREATE VOLUME IF NOT EXISTS <catalog>.<schema>.<volume>`; tutorial เดียวกันให้ผู้ใช้ Free Edition อัปโหลดไฟล์จากเครื่องผ่าน UI. คำสั่ง `databricks fs` สำหรับ Volume, `databricks workspace` สำหรับ workspace files และ `databricks jobs run-now` อยู่ในเอกสาร CLI ปรับปรุง 11 กันยายน 2026 แต่เอกสารเหล่านั้นเป็นข้อกำหนด Databricks **ทั่วไป**. การประกอบให้เป็นกระบวนการ Free Edition ด้วย CLI จึงเป็น **ข้ออนุมานที่ต้อง smoke test** ไม่ใช่คำรับรองผลิตภัณฑ์. ([tutorial; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/getting-started/dataframes)) ([คำสั่ง fs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands)) ([คำสั่ง Jobs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/jobs-commands))

| ขั้นตอน | คำตัดสิน ณ 26 ก.ย. 2026 | ขอบเขตหลักฐาน |
|---|---|---|
| GitHub CI สร้าง ตรวจ และเก็บ `mdf-release-<SHA>` | **ยืนยันจาก repository** | `release.yml` ทำ validate, compile, `package --release`, `verify-package`, pytest และ upload artifact อายุ 30 วัน; ต้องเลือก run ที่ `conclusion=success`. ([workflow; ตรวจ 26 ก.ย.](../.github/workflows/release.yml)) |
| ผู้ดูแลดาวน์โหลด artifact ของ run ด้วย `gh` | **ยืนยันสำหรับ GitHub; เอกสารคำสั่งไม่ลงวันที่** | GitHub อธิบายการดาวน์โหลด Actions artifact และ CLI `gh run download`; จัดเป็น **แหล่งพื้นหลังที่ตรวจ 26 ก.ย.** ไม่อ้างว่าผ่านเกณฑ์อายุหกเดือน. ([GitHub artifact download](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)) ([GitHub CLI manual](https://cli.github.com/manual/gh_run_download)) |
| ใช้ tag GitHub Release เป็นแหล่งรับมอบ | **ยังไม่พร้อมใน repository นี้** | `publish` job ไม่มี setup-uv/`uv sync --locked` บน runner ของตน; จะพึ่งพา assets ได้ต่อเมื่อแก้ workflow และเห็น tag run สำเร็จจริง. ([workflow; ตรวจ 26 ก.ย.](../.github/workflows/release.yml)) |
| สร้างและใช้ managed Unity Catalog Volume | **ยืนยันว่า Free Edition มี UC/Volume ใน tutorial** | ต้องมี Volume และสิทธิ์จริง; tutorial แสดง `CREATE VOLUME`. ([tutorial; 11 ก.ย.](https://docs.databricks.com/aws/en/getting-started/dataframes)) |
| OAuth U2M และ CLI upload ไป Volume | **มีเงื่อนไข** | CLI ทั่วไประบุ `auth login` และ `fs cp`; ไม่มีเอกสารเฉพาะ Free Edition ยืนยันทุก API. หากไม่ผ่าน ใช้ UI upload ที่ tutorial สาธิต. ([CLI authentication; 11 ก.ย.](https://docs.databricks.com/aws/en/dev-tools/cli/authentication)) ([คำสั่ง fs; 11 ก.ย.](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands)) |
| Workspace folder เป็นที่เก็บคอนฟิก | **มีเงื่อนไข; เป็นทางเลือก** | `workspace import --format RAW` รองรับไฟล์; ไฟล์ workspace จำกัด 500 MB ต่อไฟล์. เป็นพื้นที่คนละชนิดกับ Volume. ([workspace commands; 11 ก.ย.](https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands)) ([workspace files; 11 ก.ย.](https://docs.databricks.com/aws/en/files/workspace)) |
| Saved serverless Job รับ `release_id` | **ยืนยันสำหรับ Jobs ทั่วไป; Free Edition ต้องทดสอบปลายทาง** | Free Edition มี Jobs/serverless และเพดาน 5 concurrent tasks; Jobs ทั่วไปรับ job parameter และ `run-now`. ตัวรันคอนฟิกยังต้องสร้าง. ([ข้อจำกัด Free Edition; 25 ก.ย.](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)) ([job parameters; 11 ก.ย.](https://docs.databricks.com/aws/en/jobs/job-parameters)) |
| GitHub OIDC, service principal หรือ PAT แบบไร้ผู้ดูแล | **ไม่ยืนยัน** | Free Edition ไม่มี account console และ account-level APIs; วิธีทั่วไปที่ต้องตั้ง federation policy ระดับ account จึงไม่ควรถูกอ้างว่าใช้ได้ใน Free Edition. ไม่มีหลักฐานที่พบว่าห้ามหรือรองรับ PAT โดยเฉพาะ. ([ข้อจำกัด Free Edition; 25 ก.ย.](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)) ([federation policy; 16 ก.ย.](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-federation-policy)) |

## รับแพ็กเกจที่ผ่าน CI ตาม run และ SHA พร้อมตรวจขอบเขตความเชื่อถือ

`release.yml` ทำงานเมื่อ push ไป `master` หรือ tag `v*`; build job ใช้ `uv sync --locked`, ตรวจ data contracts, compile `dev`, สร้าง `build/dev/release`, ตรวจแพ็กเกจและรัน pytest ก่อน upload ชื่อ `mdf-release-${{ github.sha }}`. `src/mdf/package.py` คัดลอก **resolved JSON แบบ flat** ลงโฟลเดอร์นั้น แล้วสร้าง `manifest.json` ที่บันทึก SHA-256 ของแต่ละไฟล์. `verify-package` คำนวณ hash ใหม่และตรวจไฟล์ที่หาย/เกินระดับบนสุด แต่ **ไม่ตรวจลายเซ็นของ manifest**, ไม่ตรวจความเท่ากันของ `file_count` กับจำนวน entries และไม่พิสูจน์แหล่งกำเนิดหากผู้โจมตีเปลี่ยนทั้ง manifest และไฟล์. ต้องผูกการอนุมัติกับ repository, run ID, head SHA และ digest ของ manifest ที่บันทึกแยกไว้. PR artifact ชื่อ `mdf-preview-<run_id>` อายุ 7 วันเป็นคนละตัวกับ release artifact. ([release workflow](../.github/workflows/release.yml)) ([package implementation](../src/mdf/package.py)) ([PR workflow](../.github/workflows/ci.yml))

ตัวอย่าง PowerShell นี้ให้รันจาก **clean checkout ที่แยกไว้ของ commit เดียวกับ CI** และมี `gh` กับ `uv`; เปลี่ยน run ID เป็น **successful `release.yml` run** ที่อนุมัติ. ตัวอย่างหยุดถ้า `HEAD` ไม่ตรง SHA เพื่อไม่ใช้ verifier คนละรุ่น; ผู้ดูแลต้อง checkout SHA ที่แสดงใน run ก่อนเริ่มขั้น `uv sync`. `gh` manual ไม่แสดงวันปรับปรุง จึงเป็น **พื้นหลังที่ตรวจ 26 ก.ย. 2026**; ตรวจ `gh run download --help` กับเวอร์ชันที่ติดตั้งหากคำสั่งต่างจากตัวอย่าง. ([GitHub CLI run view](https://cli.github.com/manual/gh_run_view)) ([GitHub CLI run download](https://cli.github.com/manual/gh_run_download))

```powershell
$repo = 'franceZa/MetadataRegistry'
$runId = '<approved-successful-release-run-id>'
gh auth login --web
$run = gh run view $runId -R $repo --json headSha,conclusion,status,workflowName | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $run.conclusion -ne 'success' -or $run.workflowName -ne 'Release (push master)') { throw 'Selected run is not a successful release workflow run' }
$sha = $run.headSha
if ($sha -notmatch '^[0-9a-f]{40}$') { throw 'Unexpected commit SHA' }
$pkg = Join-Path (Get-Location) "downloads/$sha"
New-Item -ItemType Directory -Force -Path $pkg | Out-Null
gh run download $runId -R $repo -n "mdf-release-$sha" -D $pkg
if ($LASTEXITCODE -ne 0) { throw 'Artifact download failed' }
# ใช้ checkout ของ SHA เดียวกับ run หรือ environment ที่ติดตั้ง verifier จาก SHA นั้น
if ((git rev-parse HEAD) -ne $sha) { throw 'Checkout does not match CI head SHA' }
uv sync --locked
if ($LASTEXITCODE -ne 0) { throw 'Dependency sync failed' }
uv run mdf verify-package $pkg
if ($LASTEXITCODE -ne 0) { throw 'Manifest verification failed' }
$manifestSha256 = (Get-FileHash (Join-Path $pkg 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
"run=$runId sha=$sha manifest_sha256=$manifestSha256"
```

**อย่าใช้ source ZIP อัตโนมัติของ GitHub Release แทนแพ็กเกจที่ CI สร้าง.** เมื่อแก้ `publish` job ให้ติดตั้ง `uv` และ sync dependencies แล้วเห็น tag run สำเร็จ จึงดาวน์โหลด assets ที่ job แนบไว้ด้วย `gh release download <tag> -R franceZa/MetadataRegistry -D <dir>` และตรวจ manifest เช่นเดิม. ถ้าตั้งค่า **immutable releases** ไว้จริง สามารถตรวจ `gh release view <tag> --json isImmutable`, `gh release verify <tag>` และ `gh release verify-asset <tag> <local-file>` แยกทุก asset; การลงลายเซ็น/ความ immutable ไม่ได้เกิดขึ้นเพียงเพราะ workflow เรียก `gh release create`. Artifact attestation ก็ยังไม่มีใน workflow ปัจจุบัน จึงห้ามกล่าวว่าแพ็กเกจตอนนี้มี signed provenance. เอกสาร GitHub ส่วนนี้ไม่แสดงวันปรับปรุงในหน้าที่ตรวจและใช้เป็น **พื้นหลัง**, ส่วนสถานะ workflow มาจากไฟล์ใน repository ณ 26 ก.ย. ([immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)) ([GitHub CLI release verification](https://cli.github.com/manual/gh_release_verify-asset)) ([workflow](../.github/workflows/release.yml))

## อัปโหลดแบบผู้ใช้ไป Volume แล้วอ่านด้วย path อีกชนิดใน Job

เลือก managed Volume ภายใต้ workspace catalog/schema ที่เข้าถึงได้. ผู้ upload ต้องมี `USE CATALOG`, `USE SCHEMA`, `READ VOLUME` และ `WRITE VOLUME`; ตัวรันควรมีเพียงสิทธิ์อ่านเมื่อแยกสิทธิ์ได้. **CLI อ้าง Volume ด้วย `dbfs:/Volumes/...` ส่วนโค้ดบน compute อ่านด้วย `/Volumes/...`**; `/Workspace/...` เป็น workspace files และใช้ `databricks workspace` ไม่ใช่ `fs`. Volume เหมาะกับไฟล์คอนฟิก/สิ่งที่ส่งจาก CI เพราะเป็น non-tabular files ภายใต้ UC. Free Edition tutorial ยืนยัน UI upload เข้า Volume แต่การใช้ CLI ใน account นี้ยังต้องพิสูจน์จริง. ([Volume privileges; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/volumes/privileges)) ([คำสั่ง fs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands)) ([Unity Catalog volumes; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/volumes)) ([tutorial; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/getting-started/dataframes))

ตัวอย่างด้านล่างใช้ **full commit SHA เป็น `release_id`** ซึ่งเป็นแบบแผนที่เสนอ ไม่ใช่ field ที่ manifest ระบุ. สร้าง Volume ก่อนหนึ่งครั้งใน UI/notebook (`CREATE VOLUME IF NOT EXISTS ...`) และแทนค่า host/catalog/schema/volume. ขั้นตอน preflight ตรวจว่า directory เป้าหมายยังไม่มี; คัดลอกทีละไฟล์ **โดยไม่ใช้ `--overwrite`**; ดาวน์โหลดกลับมาตรวจเพื่อไม่ trigger งานก่อนแพ็กเกจครบ. `fs cp` ไม่ได้รับประกัน atomic publication หรือ WORM จึงต้องคง directory เดิมและจำกัด write privilege. ([คำสั่ง fs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands))

```powershell
winget install Databricks.DatabricksCLI
databricks -v
databricks auth login --host 'https://<workspace-host>'
databricks auth profiles
$profile = '<profile-created-by-login>'
databricks current-user me -p $profile
if ($LASTEXITCODE -ne 0) { throw 'Databricks OAuth login did not work in this workspace' }

$releaseId = $sha
$volumeRoot = 'dbfs:/Volumes/<catalog>/<schema>/<volume>/config-releases/dev'
$volumeDest = "$volumeRoot/$releaseId"
databricks fs ls $volumeDest -p $profile *> $null
if ($LASTEXITCODE -eq 0) { throw 'Release directory already exists; never overwrite it' }
databricks fs mkdir $volumeDest -p $profile
if ($LASTEXITCODE -ne 0) { throw 'Volume directory creation failed' }
Get-ChildItem -LiteralPath $pkg -File | ForEach-Object {
    databricks fs cp $_.FullName "$volumeDest/$($_.Name)" -p $profile
    if ($LASTEXITCODE -ne 0) { throw "Upload failed: $($_.Name)" }
}
databricks fs ls $volumeDest -p $profile
if ($LASTEXITCODE -ne 0) { throw 'Volume listing failed' }
$roundtrip = Join-Path (Get-Location) "downloads/roundtrip-$releaseId"
New-Item -ItemType Directory -Force -Path $roundtrip | Out-Null
Get-ChildItem -LiteralPath $pkg -File | ForEach-Object {
    databricks fs cp "$volumeDest/$($_.Name)" (Join-Path $roundtrip $_.Name) -p $profile
    if ($LASTEXITCODE -ne 0) { throw "Readback failed: $($_.Name)" }
}
uv run mdf verify-package $roundtrip
if ($LASTEXITCODE -ne 0) { throw 'Readback package failed verification' }
$readbackManifestHash = (Get-FileHash (Join-Path $roundtrip 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
if ($readbackManifestHash -ne $manifestSha256) { throw 'Readback manifest differs from approved manifest' }
```

ถ้า OAuth CLI ใช้ไม่ได้ใน Free Edition ให้ผู้ดูแลใช้ **New → Add or upload data → Upload files to a volume** ตาม tutorial แล้วเลือกไฟล์แต่ละไฟล์ของแพ็กเกจเข้า directory ของ release ID เดียวกัน; ยืนยันจำนวน ชื่อ และ hash ผ่านการอ่านกลับที่ใช้ได้ใน workspace ก่อน trigger. ทางเลือก workspace folder ใช้ `RAW` เพื่อรักษาชื่อ JSON/manifest ตรง ๆ; อย่าใช้ `workspace import-dir` โดยไม่ตรวจชื่อ เพราะคำสั่งนั้นลบนามสกุล notebook บางชนิด. Workspace files มีขนาดสูงสุด **500 MB ต่อไฟล์** และมีข้อจำกัดการหมดอายุสิทธิ์ของ compute ที่เอกสารอธิบายไว้; โค้ด Job ที่เลือกเส้นทางนี้ต้องอ่านจาก `/Workspace/...` ไม่ใช่ `/Volumes/...`. ([tutorial; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/getting-started/dataframes)) ([workspace commands; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands)) ([workspace files; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/files/workspace))

```powershell
$workspaceDest = "/Workspace/Shared/mdf/releases/$releaseId"
databricks workspace get-status $workspaceDest -p $profile *> $null
if ($LASTEXITCODE -eq 0) { throw 'Workspace release folder already exists' }
databricks workspace mkdirs $workspaceDest -p $profile
if ($LASTEXITCODE -ne 0) { throw 'Workspace folder creation failed' }
Get-ChildItem -LiteralPath $pkg -File | ForEach-Object {
    databricks workspace import "$workspaceDest/$($_.Name)" --file $_.FullName --format RAW -p $profile
    if ($LASTEXITCODE -ne 0) { throw "Workspace import failed: $($_.Name)" }
}
databricks workspace list $workspaceDest -p $profile
```

## เรียก saved serverless Job ด้วย release_id หลังเตรียมตัวรันคอนฟิก

**repository นี้ยังไม่มี ingestion runner สำหรับ Databricks**: `mdf` CLI ใน `src/mdf/cli.py` ทำ validate, compile, package, verify, diff และ trace ส่วน `pyproject.toml` กำหนด Python project ที่สร้าง wheel ได้แยกต่างหาก. จึงต้องสร้าง **saved Job** ที่มี stable notebook หรือ Python script อ่านแพ็กเกจจาก `/Volumes/<catalog>/<schema>/<volume>/config-releases/dev/<release_id>/`; อย่ากำหนด directory JSON นี้เป็น Python wheel library. Notebook task เหมาะกับ smoke test แรกและรับ job parameter แบบ key-value ผ่าน `dbutils.widgets.get('release_id')`; Python script task ต้องตั้ง argument array เป็น `['--release-id', '{{job.parameters.release_id}}']` ใน UI/JSON. หากภายหลังสร้าง wheel ของโค้ด runner จริง จึงกำหนด wheel task กับ environment dependency แยก และยังให้ `release_id` เลือก **config** เท่านั้น. เอกสาร Jobs ทั่วไปรองรับ notebook/script/wheel บน serverless แต่ยังไม่มีการทดสอบ Job นี้ใน Free Edition account จริง. ([CLI ใน repository](../src/mdf/cli.py)) ([project metadata](../pyproject.toml)) ([serverless Jobs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/jobs/run-serverless-jobs)) ([task parameters; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/jobs/task-parameters)) ([parameter access; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/jobs/parameter-use))

ตั้ง job-level parameter ชื่อ `release_id`, จำกัดผู้แก้ Job/ผู้สั่ง Run และให้ notebook ตรวจ ID ด้วย allowlist เช่น full SHA 40 ตัว, ประกอบ path ใต้ root คงที่, ตรวจ manifest กับทุก JSON ก่อนใช้งาน และบันทึก `release_id` กับ manifest digest ลง run log. **ค่า default ของ job parameter ไม่ใช่ขอบเขตสิทธิ์**: ผู้มี `CAN MANAGE RUN` หรือสูงกว่าสามารถ override ค่าได้. ใช้ saved Job มากกว่า `jobs submit` เพราะการ deploy นี้ต้องมี Job ที่ตรวจสอบและเรียกซ้ำได้. ตั้ง concurrency เริ่มต้นหนึ่ง run, พิจารณา queueing/automatic retry ตามผลข้างเคียงของ ingestion; Free Edition ไม่มี SLA และ quota อาจหยุด compute. ([job parameters; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/jobs/job-parameters)) ([Jobs parameter permissions; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/jobs/parameters)) ([คำสั่ง Jobs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/jobs-commands)) ([ข้อจำกัด Free Edition; 25 ก.ย. 2026](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations))

PowerShell นี้เรียก Job ที่สร้างไว้แล้วโดยส่ง JSON body ผ่านไฟล์ UTF-8 **ไม่มี BOM**; CLI ปัจจุบันกำหนด positional `JOB_ID` และรองรับ `--json @path`, `--idempotency-token`, `--no-wait`. ใช้ token ใหม่ต่อ **ความพยายามเชิงธุรกิจ** และเก็บ token เดิมไว้เมื่อ retry คำขอที่ไม่รู้ผล เพื่อไม่สร้าง run ซ้ำ. การรับ `run_id` ไม่ได้แปลว่างานสำเร็จ; ต้องตรวจ final state. ([คำสั่ง Jobs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/jobs-commands))

```powershell
$jobId = 123456789012345 # เปลี่ยนเป็น ID ของ saved Job จริง
$body = @{ job_id = $jobId; job_parameters = @{ release_id = $releaseId } }
$jsonPath = Join-Path (Get-Location) 'run-now.json'
[System.IO.File]::WriteAllText($jsonPath, ($body | ConvertTo-Json -Depth 5 -Compress), (New-Object System.Text.UTF8Encoding $false))
$requestToken = [guid]::NewGuid().ToString('N')
$submitted = databricks jobs run-now $jobId --json "@$jsonPath" --idempotency-token $requestToken --no-wait -p $profile -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $submitted.run_id) { throw 'Job trigger failed' }
$databricksRunId = $submitted.run_id
"job=$jobId run=$databricksRunId release_id=$releaseId token=$requestToken"
databricks jobs get-run $databricksRunId -p $profile -o json
```

## ทดสอบแบบอ่านอย่างเดียวก่อนประมวลผล และย้อนกลับด้วย ID เดิมที่ตรวจแล้ว

smoke test ที่ปฏิบัติได้คือสร้าง **Job notebook task แบบอ่านอย่างเดียว** ที่รับ `release_id`, ตรวจ regex `^[0-9a-f]{40}$`, อ่าน `/Volumes/.../config-releases/dev/<release_id>/manifest.json`, เทียบรายการชื่อไฟล์กับไฟล์ JSON ที่พบ, คำนวณ SHA-256 ของทุกไฟล์ตาม manifest แล้วอ่าน JSON สักไฟล์เพื่อพิสูจน์สิทธิ์และ path. ให้ fail เมื่อ ID ผิด, manifest หาย, hash ผิด หรือมีไฟล์เกิน; อย่าให้ test นี้เขียน Delta/external systems. หลัง upload ให้รันด้วยคำสั่งข้างต้น, รอ `life_cycle_state=TERMINATED` และ `result_state=SUCCESS`, ตรวจ log ว่าบันทึก ID/digest ที่อนุมัติ; หาก `SKIPPED`, timeout, quota shutdown หรือ auth/privilege ผิด ให้หยุด rollout. การตรวจกลับบนเครื่องด้วย `mdf verify-package` และ hash manifest ในขั้นก่อนหน้าช่วยจับความเสียหายระหว่าง upload; การตรวจใน Job ช่วยจับการแก้ภายหลัง แต่ **ไม่มีลายเซ็นที่ผูก manifest กับผู้สร้าง** ใน workflow ปัจจุบัน. ([package implementation](../src/mdf/package.py)) ([Volume privileges; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/volumes/privileges)) ([ข้อจำกัด Free Edition; 25 ก.ย. 2026](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations))

เก็บ directory release ก่อนหน้าไว้และ **rollback โดยเรียก saved Job เดิมด้วย `release_id` ก่อนหน้าที่ตรวจแล้ว**; ใช้ JSON/คำสั่ง `jobs run-now` เดิมโดยเปลี่ยนเพียง `$releaseId`. วิธีนี้คืนค่า **คอนฟิกที่ Job จะอ่านใน run ถัดไป** ไม่ย้อนการเขียนตารางหรือผลข้างเคียงของ run ก่อนหน้า. หาก ingestion มีผลข้างเคียง ต้องออกแบบ idempotency หรือขั้นตอนกู้ข้อมูลแยก. อย่าแก้หรือ overwrite directory เดิมเพื่อทำ rollback เพราะจะตัดความเชื่อมโยง ID ↔ ไฟล์; Volume เองไม่ได้รับรอง immutability. บันทึกหลักฐาน `(repo, GitHub run ID, SHA, artifact name, manifest SHA-256, ผู้อนุมัติ, Volume path, Databricks job/run ID, final state)` เป็นร่องรอยส่งมอบ. นี่เป็น **ข้อเสนอเชิงปฏิบัติ** ที่อนุมานจาก CLI และโครงสร้างแพ็กเกจ ไม่ใช่ฟีเจอร์ rollback อัตโนมัติของ Databricks. ([คำสั่ง fs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands)) ([คำสั่ง Jobs; 11 ก.ย. 2026](https://docs.databricks.com/aws/en/dev-tools/cli/reference/jobs-commands))

## Conclusion

ขอบเขตที่พิสูจน์ได้ในวันนี้คือ **CI ตรวจคอนฟิกแล้วส่ง artifact ให้ผู้ดูแลรับมอบ** และ Free Edition มี UC/serverless Jobs สำหรับทดลองเส้นทาง upload/run. จุดเปลี่ยนจาก “มีไฟล์ใน Volume” เป็น “deployed release ที่เชื่อถือได้” อยู่ที่การยืนยัน SHA/run, hash manifest ที่เก็บนอกแพ็กเกจ, การอ่านกลับและตรวจใน Job รวมถึง runner ที่สร้างแยกจากแพ็กเกจคอนฟิก. ก่อนใช้เป็นงานประจำต้องผ่าน smoke test บน workspace จริงและแก้ tag `publish` job; หากต้องการ unattended GitHub deployment หรือ signed provenance ให้ตรวจความสามารถของ account และเพิ่ม workflow/การตั้งค่าที่เกี่ยวข้องก่อนอ้างว่าใช้งานได้.

**ขอบเขตวันที่ของแหล่งอ้างอิง:** หน้าทางการ Databricks ที่ใช้ตัดสินข้างต้นแสดงวันปรับปรุง 11, 16, 17 หรือ 25 ก.ย. 2026 จึงอยู่ในช่วงหกเดือนที่กำหนด. หน้า GitHub Docs และ `cli.github.com/manual` ที่ตรวจไม่แสดงวันปรับปรุง จึงเป็น **เอกสารพื้นหลังที่ตรวจเมื่อ 26 ก.ย. 2026** ไม่ใช่หลักฐานว่าเผยแพร่/ปรับปรุงหลัง 26 มี.ค. 2026. ไฟล์ repository เป็นหลักฐานสภาพโค้ดที่ตรวจเมื่อ 26 ก.ย. 2026 ไม่ใช่เอกสารผลิตภัณฑ์ที่ลงวันที่. ไม่มีการเข้าถึง Free Edition workspace, successful live run หรือ GitHub Release จริงในการศึกษานี้.
