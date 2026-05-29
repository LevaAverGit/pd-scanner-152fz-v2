# Route Table

## Public Pages

| Method | Path | Description | PD Scanner Phase |
|--------|------|-------------|-----------------|
| GET | / | Homepage with modal lead form | Page crawl, form detection |
| GET | /about | About page with company/contact info | Entity extraction |
| GET | /services | Services page with 152-FZ references | Policy keyword detection |
| GET | /pricing | Pricing page | Page crawl |
| GET | /request-demo | Primary demo request form (all PD fields) | Form analysis, consent check |
| GET | /contact | Contact form | Form analysis, consent check |
| GET | /webinar | Webinar registration form (JS submit) | Form analysis |
| GET | /careers | Job application form | Form analysis |
| GET | /privacy | Privacy policy HTML (profile-adaptive) | Policy completeness check |
| GET | /terms | Terms of service | Legal doc detection |
| GET | /cookies | Cookie policy | Cookie compliance check |
| GET | /privacy.pdf | Privacy policy PDF | Document download check |
| GET | /privacy.docx | Privacy policy DOCX | Document download check |

## Form Submission Endpoints

| Method | Path | Description | PD Scanner Phase |
|--------|------|-------------|-----------------|
| POST | /submit | Main form handler (HTML forms) | Synthetic submission, routing analysis |
| POST | /api/lead | JSON lead capture (modal form) | API endpoint detection |
| POST | /webhook/mock | Mock webhook receiver | Vendor/routing detection |
| POST | /crm/mock | Mock CRM endpoint | Third-party routing detection |

## Mock Services (Third-Party Simulation)

| Method | Path | Description | PD Scanner Phase |
|--------|------|-------------|-----------------|
| GET | /mock/analytics.js | Analytics SDK script (loaded on ALL pages) | Vendor script detection |
| POST | /mock/analytics/collect | Analytics event collection | Network call analysis |
| GET | /mock/pixel.gif | Tracking pixel (bad_compliance only) | Tracking pixel detection |
| GET | /mock/crm.js | CRM SDK script (bad_compliance only) | Vendor script detection |

## Admin Panel

| Method | Path | Description | Authentication |
|--------|------|-------------|---------------|
| GET | /admin/login | Login page | None required |
| POST | /admin/login | Login handler | None required |
| GET | /admin/logout | Logout | Cookie |
| GET | /admin/submissions | Submission log | Cookie |
| GET | /admin/routing-log | Routing events log | Cookie |
| GET | /admin/consent-log | Consent events log | Cookie |
| GET | /admin/processors | Processor events log | Cookie |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/status | Health check + current profile |
| GET | /api/profile | Get current profile |
| POST | /api/profile/{name} | Set profile (good/mixed/bad_compliance) |
