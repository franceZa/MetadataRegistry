mode manual — ทำทีละขั้น
release ที่ใช้คือ mdf-f145479894d6 ซึ่งยังไม่เคยส่ง ตอนนี้ยังไม่มีโฟลเดอร์ของ release นี้ใน Volume ขั้นตอนข้างล่างสร้างจาก scripts/next_steps.py ตัวเดียวกับที่ใช้ทำ Summary:

M-1 เปิด หน้า Release แล้วดาวน์โหลดครบ 8 ไฟล์ (6 × \*.resolved.json, manifest.json, validation-report.json)
M-2 ใน Databricks ไปที่ Catalog → dev_catalog → ops → Volume files → โฟลเดอร์ releases → Create directory ตั้งชื่อ mdf-f145479894d6
M-3 เข้าโฟลเดอร์นั้น → Upload to this volume → อัปโหลด 7 ไฟล์ ยกเว้น manifest.json ก่อน แล้วค่อยอัปโหลด manifest.json เป็นไฟล์สุดท้าย
M-4 เปิด SQL Editor → วางเนื้อหาทั้งไฟล์ sql/manual/register_release.sql (อยู่ใน repo บน master) → ตั้ง parameter release_id = mdf-f145479894d6 → Run all
M-5 ดูผล statement สุดท้าย ต้องได้ REGISTERED 1 แถว, actor = manual-ui และ manifest_sha256 ต้องเป็น e4ffbfc823aeb0b1e49fdcaa63a7c997e977ad4466db8afe5deaa0530925f335 (เลขเดียวกับ digest ของ manifest.json บนหน้า Release)
M-6 วางเนื้อหาไฟล์ sql/manual/activate_release.sql → release_id = mdf-f145479894d6 → Run all
M-7 ผลสุดท้ายต้องขึ้น active_release_id = mdf-f145479894d6
กลับไปใช้ release เดิม: ทำ M-6 ซ้ำอีกรอบด้วย release_id = mdf-d3ea0d559e04 ซึ่งเป็นวิธี rollback ของ mode manual ด้วย
