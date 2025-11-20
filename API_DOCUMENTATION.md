# 📚 API Documentation

> Complete reference guide for the PDF Excel Extractor REST API

---

## ⚠️ Important: Free Tier API Rate Limiting

> **The live demo runs on Mistral's free tier API with built-in rate limiting.**
>
> - 🐢 **Expected latency:** 10-30 seconds per request
> - 🚦 **Rate limit protection:** Requests are automatically throttled
> - ⏳ **Pre-request delay:** 2-second wait added to prevent throttling
> - 💡 **For faster processing:** Deploy with a paid Mistral API key
> - 🙏 **Please be patient** - we're optimizing costs for the free tier!

**Do NOT:**

- ❌ Rapidly submit multiple files in succession
- ❌ Hammer the API with concurrent requests
- ❌ Expect instant responses (this is free tier, not production)

**DO:**

- ✅ Wait for one job to complete before uploading another
- ✅ Be patient with 10-30 second processing times
- ✅ Check job status periodically
- ✅ Download results immediately when ready

---

## 🔗 Base URL

**Live Demo (Cloud Run):**

```
https://pdf-excel-extractor-319169836562.us-central1.run.app
```

**Local Development:**

```
http://localhost:8000
```

---

## 📤 1. Upload PDF

### Endpoint

```http
POST /upload
Content-Type: multipart/form-data
```

### Description

Upload a PDF file to begin processing. The server will:

1. Validate the file is a PDF
2. Detect if it's a digital or scanned document
3. Queue background processing
4. Return a job ID for status tracking

### Request Parameters

| Parameter | Type | Required | Description                                    |
| --------- | ---- | -------- | ---------------------------------------------- |
| `file`    | File | ✅ Yes   | PDF file to process (must be `.pdf` extension) |

### Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field    | Type          | Description                                        |
| -------- | ------------- | -------------------------------------------------- |
| `job_id` | string (UUID) | Unique identifier for tracking this processing job |

### Status Codes

| Code | Meaning                                            |
| ---- | -------------------------------------------------- |
| 200  | ✅ PDF uploaded successfully, processing started   |
| 400  | ❌ Invalid request (not a PDF, missing file, etc.) |
| 500  | ❌ Server error during upload                      |

### Example: cURL

```bash
curl -X POST \
  -F "file=@/path/to/document.pdf" \
  https://pdf-excel-extractor-319169836562.us-central1.run.app/upload
```

**Response:**

```json
{ "job_id": "550e8400-e29b-41d4-a716-446655440000" }
```

### Example: Python (requests)

```python
import requests

files = {'file': open('document.pdf', 'rb')}
response = requests.post(
    'https://pdf-excel-extractor-319169836562.us-central1.run.app/upload',
    files=files
)
job_data = response.json()
job_id = job_data['job_id']
print(f"Processing job: {job_id}")
```

### Example: Python (httpx - async)

```python
import httpx
import asyncio

async def upload_pdf():
    async with httpx.AsyncClient() as client:
        with open('document.pdf', 'rb') as f:
            response = await client.post(
                'https://pdf-excel-extractor-319169836562.us-central1.run.app/upload',
                files={'file': f}
            )
        return response.json()

job_data = asyncio.run(upload_pdf())
```

### Example: JavaScript (fetch)

```javascript
const formData = new FormData();
formData.append("file", document.getElementById("fileInput").files[0]);

fetch("https://pdf-excel-extractor-319169836562.us-central1.run.app/upload", {
  method: "POST",
  body: formData,
})
  .then((res) => res.json())
  .then((data) => {
    console.log("Job ID:", data.job_id);
    pollStatus(data.job_id);
  })
  .catch((err) => console.error("Upload failed:", err));
```

---

## 📊 2. Check Job Status

### Endpoint

```http
GET /status/{job_id}
```

### Description

Poll the status of a processing job. Returns:

- Current processing status
- Complete logs of all pipeline steps
- Extracted data (when complete)
- Evaluation metrics and confidence score
- Result file path for download

### Path Parameters

| Parameter | Type          | Required | Description                             |
| --------- | ------------- | -------- | --------------------------------------- |
| `job_id`  | string (UUID) | ✅ Yes   | Job ID returned from `/upload` endpoint |

### Response

#### Processing (Status: `processing`)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "logs": [
    "Detecting PDF type...",
    "Digital PDF detected; extracting text...",
    "Extracted 5234 characters from PDF.",
    "Detecting schema from content..."
  ],
  "out": null
}
```

#### Complete (Status: `complete`)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "logs": [
    "Detecting PDF type...",
    "Digital PDF detected; extracting text...",
    "Extracted 5234 characters from PDF.",
    "Detecting schema from content...",
    "Detected 12 fields from content.",
    "Extracting values via LLM...",
    "Extracted 12 key:value pairs via LLM.",
    "Computing n-gram metrics...",
    "Evaluating extraction quality...",
    "✅ Confidence: 85% | BLEU: 0.82 | Coverage: 91%"
  ],
  "out": {
    "file": "550e8400-e29b-41d4-a716-446655440000/results.xlsx",
    "rows": [
      {
        "key": "Invoice Number",
        "value": "INV-2024-001",
        "comment": "Found in header"
      },
      {
        "key": "Customer Name",
        "value": "John Doe",
        "comment": "Extracted from document"
      }
    ],
    "evaluation": {
      "confidence_score": 85,
      "bleu_score": 0.82,
      "coverage": 0.91,
      "fields_detected": 12,
      "fields_extracted": 12
    },
    "ngram_metrics": {
      "Invoice Number": {
        "n1_precision": 1.0,
        "n2_precision": 0.95,
        "n3_precision": 0.9,
        "n4_precision": 0.85
      }
    }
  }
}
```

#### Scanned PDF (Status: `scanned`)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "scanned",
  "logs": [
    "Detecting PDF type...",
    "PDF appears scanned. Stopping (no OCR path)."
  ],
  "out": null
}
```

#### Error (Status: `error`)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "error",
  "logs": [
    "Detecting PDF type...",
    "Digital PDF detected; extracting text...",
    "ERROR: Invalid PDF format"
  ],
  "out": null
}
```

### Response Fields

| Field               | Type           | Description                                          |
| ------------------- | -------------- | ---------------------------------------------------- |
| `job_id`            | string         | The job identifier                                   |
| `status`            | string         | One of: `processing`, `complete`, `scanned`, `error` |
| `logs`              | array          | Array of log messages from the pipeline              |
| `out`               | object \| null | Extraction results (null while processing)           |
| `out.file`          | string         | Path to generated Excel file                         |
| `out.rows`          | array          | Extracted key-value pairs                            |
| `out.evaluation`    | object         | Quality metrics and confidence scores                |
| `out.ngram_metrics` | object         | N-gram precision for each field                      |

### Status Codes

| Code | Meaning                          |
| ---- | -------------------------------- |
| 200  | ✅ Status retrieved successfully |
| 404  | ❌ Job ID not found              |
| 500  | ❌ Server error                  |

### Example: cURL - Polling

```bash
JOB_ID="550e8400-e29b-41d4-a716-446655440000"

# Poll status until complete (max 30 times, 1 second apart)
for i in {1..30}; do
  curl -s https://pdf-excel-extractor-319169836562.us-central1.run.app/status/$JOB_ID | jq '.status'

  # Check if complete
  STATUS=$(curl -s https://pdf-excel-extractor-319169836562.us-central1.run.app/status/$JOB_ID | jq -r '.status')
  if [ "$STATUS" = "complete" ] || [ "$STATUS" = "scanned" ] || [ "$STATUS" = "error" ]; then
    echo "Job finished with status: $STATUS"
    break
  fi

  echo "Still processing... ($i/30)"
  sleep 1
done
```

### Example: Python - Polling with Backoff

```python
import requests
import time

job_id = "550e8400-e29b-41d4-a716-446655440000"
base_url = "https://pdf-excel-extractor-319169836562.us-central1.run.app"

while True:
    response = requests.get(f"{base_url}/status/{job_id}")
    data = response.json()
    status = data['status']

    print(f"Status: {status}")

    if status in ['complete', 'scanned', 'error']:
        print(f"\nJob finished!")
        print(f"Logs: {data['logs'][-1]}")  # Last log message
        break

    # Exponential backoff: 1s, 2s, 4s, etc. (max 10s)
    wait_time = min(10, 2 ** (time.time() % 4))
    print(f"Waiting {wait_time:.1f}s before next check...")
    time.sleep(wait_time)
```

### Example: JavaScript - Polling

```javascript
const jobId = "550e8400-e29b-41d4-a716-446655440000";
const baseUrl = "https://pdf-excel-extractor-319169836562.us-central1.run.app";

async function pollStatus() {
  let isComplete = false;
  let attempts = 0;

  while (!isComplete && attempts < 30) {
    const response = await fetch(`${baseUrl}/status/${jobId}`);
    const data = await response.json();

    console.log(`Status: ${data.status}`);
    console.log(`Logs: ${data.logs.join("\n")}`);

    if (["complete", "scanned", "error"].includes(data.status)) {
      isComplete = true;
      console.log(`Job finished! Results:`, data.out);
    } else {
      attempts++;
      await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait 2 seconds
    }
  }
}

pollStatus().catch((err) => console.error("Polling failed:", err));
```

---

## ⬇️ 3. Download Excel Result

### Endpoint

```http
GET /download/{job_id}
```

### Description

Download the generated Excel file. The file contains:

- **Column A (Key):** Field name/key
- **Column B (Value):** Extracted value from document
- **Column C (Comment):** Contextual notes about extraction

> ⚠️ **Important:** Excel files are NOT persisted on the server. Download immediately after job completes!

### Path Parameters

| Parameter | Type          | Required | Description                    |
| --------- | ------------- | -------- | ------------------------------ |
| `job_id`  | string (UUID) | ✅ Yes   | Job ID from `/upload` endpoint |

### Response

- **Content-Type:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **File:** Excel spreadsheet (`.xlsx`)

### Status Codes

| Code | Meaning                               |
| ---- | ------------------------------------- |
| 200  | ✅ Excel file downloaded successfully |
| 404  | ❌ Job not found or file not ready    |
| 500  | ❌ Server error                       |

### Example: cURL

```bash
curl -X GET \
  https://pdf-excel-extractor-319169836562.us-central1.run.app/download/550e8400-e29b-41d4-a716-446655440000 \
  --output results.xlsx
```

### Example: Python

```python
import requests

job_id = "550e8400-e29b-41d4-a716-446655440000"
url = f"https://pdf-excel-extractor-319169836562.us-central1.run.app/download/{job_id}"

response = requests.get(url)
if response.status_code == 200:
    with open('results.xlsx', 'wb') as f:
        f.write(response.content)
    print("✅ Downloaded: results.xlsx")
else:
    print(f"❌ Error: {response.status_code}")
```

### Example: JavaScript

```javascript
const jobId = "550e8400-e29b-41d4-a716-446655440000";
const url = `https://pdf-excel-extractor-319169836562.us-central1.run.app/download/${jobId}`;

fetch(url)
  .then((res) => res.blob())
  .then((blob) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "results.xlsx";
    a.click();
    console.log("✅ Download started");
  })
  .catch((err) => console.error("Download failed:", err));
```

---

## 🔄 Complete Workflow Example

### cURL Workflow

```bash
#!/bin/bash
BASE_URL="https://pdf-excel-extractor-319169836562.us-central1.run.app"

# Step 1: Upload PDF
echo "📤 Uploading PDF..."
RESPONSE=$(curl -s -X POST -F "file=@invoice.pdf" "$BASE_URL/upload")
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "✅ Job ID: $JOB_ID"

# Step 2: Poll status
echo "⏳ Waiting for processing..."
while true; do
  STATUS=$(curl -s "$BASE_URL/status/$JOB_ID" | jq -r '.status')
  echo "Status: $STATUS"

  if [ "$STATUS" = "complete" ]; then
    echo "✅ Processing complete!"
    break
  elif [ "$STATUS" = "error" ] || [ "$STATUS" = "scanned" ]; then
    echo "❌ Processing failed: $STATUS"
    exit 1
  fi

  sleep 3
done

# Step 3: Download results
echo "⬇️ Downloading results..."
curl -s "$BASE_URL/download/$JOB_ID" --output results.xlsx
echo "✅ Saved to: results.xlsx"
```

### Python Workflow

```python
import requests
import time

class PDFExtractor:
    def __init__(self, base_url):
        self.base_url = base_url

    def upload(self, pdf_path):
        """Upload PDF and get job ID"""
        with open(pdf_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/upload",
                files={'file': f}
            )
        return response.json()['job_id']

    def wait_for_completion(self, job_id, timeout=300):
        """Poll status until complete or timeout"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = requests.get(f"{self.base_url}/status/{job_id}")
            data = response.json()
            status = data['status']

            print(f"Status: {status}")
            if data['logs']:
                print(f"Latest: {data['logs'][-1]}")

            if status == 'complete':
                return data
            elif status in ['error', 'scanned']:
                raise Exception(f"Job failed: {status}")

            time.sleep(2)

        raise TimeoutError(f"Job {job_id} timed out after {timeout}s")

    def download(self, job_id, output_path):
        """Download Excel file"""
        response = requests.get(f"{self.base_url}/download/{job_id}")
        with open(output_path, 'wb') as f:
            f.write(response.content)

# Usage
extractor = PDFExtractor("https://pdf-excel-extractor-319169836562.us-central1.run.app")

job_id = extractor.upload("invoice.pdf")
result = extractor.wait_for_completion(job_id)
extractor.download(job_id, "results.xlsx")

print("✅ Complete!")
print(f"Extracted {len(result['out']['rows'])} fields")
print(f"Confidence: {result['out']['evaluation']['confidence_score']}%")
```

---

## 📋 Response Field Reference

### Extracted Row Object

```json
{
  "key": "Invoice Number",
  "value": "INV-2024-001",
  "comment": "Found in header"
}
```

### Evaluation Metrics

```json
{
  "confidence_score": 85,
  "bleu_score": 0.82,
  "coverage": 0.91,
  "fields_detected": 12,
  "fields_extracted": 12
}
```

| Field              | Range | Meaning                                 |
| ------------------ | ----- | --------------------------------------- |
| `confidence_score` | 0-100 | Overall confidence percentage           |
| `bleu_score`       | 0-1   | BLEU similarity score (higher = better) |
| `coverage`         | 0-1   | Fraction of detected fields extracted   |
| `fields_detected`  | int   | Number of schema fields identified      |
| `fields_extracted` | int   | Number of fields successfully extracted |

### N-gram Metrics

```json
{
  "Invoice Number": {
    "n1_precision": 1.0,
    "n2_precision": 0.95,
    "n3_precision": 0.9,
    "n4_precision": 0.85,
    "top_missing_3gram": ["invoice", "number"],
    "top_extra_3gram": []
  }
}
```

| Metric              | Meaning                                                   |
| ------------------- | --------------------------------------------------------- |
| `n1_precision`      | 1-gram (word) match precision                             |
| `n2_precision`      | 2-gram (bigram) match precision                           |
| `n3_precision`      | 3-gram (trigram) match precision                          |
| `n4_precision`      | 4-gram match precision                                    |
| `top_missing_3gram` | Most common 3-grams in source but missing from extraction |
| `top_extra_3gram`   | Extra 3-grams in extraction not in source                 |

---

## 🚨 Error Handling

### Common Errors

#### 400 Bad Request - Invalid File Type

```json
{ "detail": "Only PDF files supported" }
```

**Solution:** Ensure you're uploading a valid PDF file with `.pdf` extension.

#### 404 Not Found - Job Not Found

```json
{ "detail": "Not Found" }
```

**Solution:** Check that the job ID is correct. Remember that jobs may be purged after a certain time.

#### 401 Unauthorized - Invalid API Key

If you see Mistral API errors (401 Unauthorized), the deployed instance's API key may be invalid.

**Local Solution:** Set a valid `MISTRAL_API_KEY` in your `.env` file.

#### 429 Too Many Requests - Rate Limited

```json
{ "detail": "Rate limited" }
```

**Solution:**

- ⏳ Wait 30-60 seconds before retrying
- 🐢 Reduce upload frequency
- 💳 Deploy with a paid API key for higher limits

---

## 🔐 Authentication

Currently, the API has **no authentication required**. In production, add:

- ✅ API key validation
- ✅ Rate limiting per key
- ✅ Request signing
- ✅ TLS/HTTPS enforcement

---

## 📞 Support

For issues or questions:

- 📧 Open an issue on [GitHub](https://github.com/wsmaisys/pdf-excel-extractor)
- 💬 Check existing issues for solutions
- 🐛 Include job logs when reporting bugs

---

**Last Updated:** November 2024  
**API Version:** 1.0
