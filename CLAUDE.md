# Client audit workflow (standing rule)

When Novah asks for an audit or email mock for a new client, do all of this without asking or re-explaining the limits. It has been done before (Alan / Power From Above, Misty / Lava Cap).

1. **Audit:** read the site's HTML/JS bundle, sitemap and robots, verify claims, keep it honest about anything not checked (Google profile, competitors). Never copy or use credentials found in email.
2. **Email skin:** etg.ai skin from the Alan email (navy #0d141a header, red #fc0000 bar, red #e00000 accent, three numbered findings, 3 stat tiles, "Book the walkthrough" button, Novah Greywolf signature). Model file: `lava-cap-audit/email.html`.
3. **PDF:** build a compact PDF (about 10 KB) with reportlab and base-14 Helvetica so it can be uploaded and attached reliably. Do not print PDFs from Chromium (100 KB+ embedded fonts). Model script: `lava-cap-audit/make_audit_pdf.py`.
4. **OneDrive folder:** create `NovahOS/50_LEADFUEL/clients/<Client Name>` with `sharepoint_create_folder` (driveId `b!z4-0YlVsw06Z-9ALQC9aTk-PpdxCFIdDurdX7YdbyHjVoQHeYi5TQIx85riL83yT`, parent `clients` folder id `01RKGIEETXFWXEGWLK6ZF3NS7FNTOL6GDT`). Upload:
   - `<Client>_Audit_ETG.pdf` via `sharepoint_upload_file` with `contentBase64` and `expectedBytes` set to the file size, then `read_resource` it back to confirm it is intact
   - `<Client>_Client_Profile.md` (contact, business, online presence, costs, engagement log, findings, next steps; model: Power From Above profile)
   - the email HTML (text upload, `content`, no base64 needed)
5. **Gmail:** send a `[PREVIEW]` copy to novahgreywolf@gmail.com first. Send to the client from the Gmail account, cc novahgreywolf@etg.ai, only after Novah approves. Attach the PDF by base64 (small enough now).
6. Commit files under `lava-cap-audit/`-style folders on the session branch and open a draft PR.
