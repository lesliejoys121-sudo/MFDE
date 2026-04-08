# ✅ Verification Guide for Judges

This document summarizes the available methods to verify that the **Misleading Feedback Decision Environment (MFDE)** is fully functional and OpenEnv-compliant.

---

### 🟢 1. Visual Dashboard (Manual Triage)
The project root now features an interactive **Gmail-style AI Triage Dashboard**. Judges can "log in" to manually classify emails and visualize the misleading feedback loops.
- **Link**: [https://lesliejoy-mfde.hf.space/](https://lesliejoy-mfde.hf.space/)
- **Credentials**:
  - **Username**: `admin`
  - **Password**: `mfde2024`
- **Expected result**: You should see a professional inbox list. Clicking an email allows you to manually "Reply", "Ignore", or "Escalate" and see the immediate (potentially noisy) reward.

### 🛠️ 2. Interactive API Testing (Swagger Docs)
You can manually trigger specific environment actions using the FastAPI interactive documentation.
- **Link**: [https://lesliejoy-mfde.hf.space/docs](https://lesliejoy-mfde.hf.space/docs)
- **Instructions**: 
  1. Expand the **POST /reset** endpoint.
  2. Click **Try it out**.
  3. Enter `{"task": "easy"}` and click **Execute**.
  4. You will receive a JSON response containing an email triage observation.

### 🤖 3. Automated Script Validation
To run the project's internal validation script (which checks the Space connectivity, Docker build, and OpenEnv YAML schema):
```bash
# From the project root
chmod +x validate-submission.sh
./validate-submission.sh https://lesliejoy-mfde.hf.space .
```

### ⚡ 4. Quick CURL Test
For a pure terminal verification of the /reset pipeline:
```bash
curl -X POST https://lesliejoy-mfde.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "easy"}'
```

---

### 📦 Key Submission Details
- **Space Name**: Lesliejoy/MFDE
- **Topic**: Email Triage under Noisy Feedback
- **Compliance**: OpenEnv 1.2.0
- **Primary Logic**: NLP Classification & Reward Calibration
