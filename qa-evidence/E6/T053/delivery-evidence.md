# Delivery evidence — mdf-b255065b505d

- actor: u2m · catalog: dev_catalog · target: dev · started: 2026-10-05T15:34:19Z
- CD-1: https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-b255065b505d · downloaded mdf-b255065b505d.zip · extracted via scripts/safe_unzip.py
- CD-2: verify OK · manifest_sha256 `4704afd38d1fd99e110c2a99af25275e32cf724ee0cac617da1f5f320a809e7f` · file_count 9
- CD-3: copied 11 files · manifest.json last
- CD-4: copy-back verify OK · manifest_sha256 matches CD-2

```
$ databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-b255065b505d
cc
manifest.json
validation-report.json
```
- CD-5: bundle deploy -t dev OK
- CD-6: job run (register) OK · run: https://<host>/jobs/945186884866349/runs/988507787574430?o=3911646557004951
- CD-7: registry has exactly 1 REGISTERED row · manifest_sha256 + file_count match
- CD-8: job run (activate) OK · run: https://<host>/jobs/945186884866349/runs/513016927274223?o=3911646557004951
- CD-8: latest ACTIVATED = mdf-b255065b505d · bundle var active_release_id set

```
registry rows for mdf-b255065b505d: [["REGISTERED", "4704afd38d1fd99e110c2a99af25275e32cf724ee0cac617da1f5f320a809e7f", "9", "/Volumes/dev_catalog/ops/files/releases/mdf-b255065b505d", "u2m", "2026-10-05 15:36:35.097825"], ["ACTIVATED", "4704afd38d1fd99e110c2a99af25275e32cf724ee0cac617da1f5f320a809e7f", "9", "/Volumes/dev_catalog/ops/files/releases/mdf-b255065b505d", "u2m", "2026-10-05 15:38:05.184301"]]
```
- copied_this_run: 1 · finished: 2026-10-05T15:38:45Z
