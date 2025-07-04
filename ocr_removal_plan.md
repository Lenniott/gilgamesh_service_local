# OCR Removal Plan - Comprehensive List

## 📋 **WHAT NEEDS TO BE REMOVED:**

### **1. Dependencies & Requirements**
- **requirements.txt**: Remove `easyocr`, `pytesseract`, `pillow`, `Pillow==10.1.0`
- **Dockerfile**: Remove `tesseract-ocr` system dependency
- **README.md**: Remove OCR installation instructions and mentions

### **2. Core Files to Delete/Modify**
- **🗑️ DELETE**: `app/ocr_utils.py` (entire file - 60 lines of OCR code)
- **✏️ MODIFY**: `app/utils.py` (remove image processing functions)
- **✏️ MODIFY**: `app/media_utils.py` (remove OCR imports and calls)
- **✏️ MODIFY**: `app/database.py` (remove OCR text fields)

### **3. Test Files to Update**
- **✏️ MODIFY**: `tests/test_services/test_process_url.py` (remove OCR mocks)

### **4. Documentation to Update**
- **✏️ MODIFY**: `README.md` (remove OCR features from documentation)
- **✏️ MODIFY**: `curl_commands.md` (remove OCR text from examples)
- **✏️ MODIFY**: `plan.md` (remove OCR tasks)

### **5. SQL/Database Files to Update**
- **✏️ MODIFY**: `insert_media_queries.sql` (remove OCR text references)
- **✏️ MODIFY**: `insert_media_queries_with_variables.sql` (remove OCR variables)
- **✏️ MODIFY**: `n8n_sql_queries.sql` (remove OCR text inserts)

---

## 🎯 **DETAILED REMOVAL STEPS:**

### **Step 1: Remove Dependencies**
```bash
# requirements.txt - REMOVE these lines:
- pillow
- pytesseract
- Pillow==10.1.0
- easyocr
```

```dockerfile
# Dockerfile - REMOVE this line:
- tesseract-ocr \
```

### **Step 2: Delete OCR Module**
```bash
# DELETE entire file:
rm app/ocr_utils.py
```

### **Step 3: Clean app/utils.py**
**REMOVE** these functions:
- `resize_image_if_needed()` (lines 13-27)
- PIL import (line 4)

**KEEP** these functions:
- `clean_text()` (still needed for general text cleaning)
- `is_valid_url()` (needed for URL validation)

### **Step 4: Clean app/media_utils.py**
**REMOVE** these imports (line 8):
```python
from app.ocr_utils import ocr_image, EASYOCR_READER
```

**REMOVE** these code blocks:
- Lines 110-115: OCR processing for video frames
- Lines 149-152: OCR processing for images
- Line 120: `"text": ocr_text,` (replace with empty string)

### **Step 5: Clean app/database.py**
**MODIFY** these functions to remove OCR text handling:
- `_insert_video_scene()` (line 191)
- `_insert_image()` (line 227)

### **Step 6: Update Tests**
**REMOVE** from `tests/test_services/test_process_url.py`:
- Line 6: `from app.ocr_utils import ocr_image`
- Lines 43-47: `mock_ocr()` fixture
- All `mock_ocr` parameters in test functions

### **Step 7: Update Response Structure**
**MODIFY** JSON response to remove text fields:
- `videos[].scenes[].text` → Remove entirely
- `images[].text` → Remove entirely

### **Step 8: Update SQL Queries**
**REMOVE** OCR-related columns from inserts:
- `onscreen_text` from `gilgamesh_sm_video_scenes`
- `descriptive_text` from `gilgamesh_sm_images`

---

## 🔄 **NEW SIMPLIFIED WORKFLOW:**

**BEFORE (with OCR):**
1. Download media
2. Extract video scenes
3. **❌ Run OCR on frames**
4. **❌ Run OCR on images**
5. Transcribe audio
6. Return JSON with text + transcripts

**AFTER (no OCR):**
1. Download media
2. Extract video scenes (timestamps only)
3. ~~Run OCR on frames~~ ← **REMOVED**
4. ~~Run OCR on images~~ ← **REMOVED**
5. Transcribe audio
6. Return JSON with timestamps + transcripts only

---

## ✅ **BENEFITS:**
- **🚀 Faster processing** (no OCR overhead)
- **📦 Smaller Docker image** (no Tesseract)
- **🔧 Fewer dependencies** (no PIL, EasyOCR, PyTesseract)
- **💾 Simpler database** (no text fields)
- **🧹 Cleaner codebase** (remove 60+ lines of OCR code)

---

## 🚨 **IMPACT ON EXISTING DATA:**
- Database columns `onscreen_text` and `descriptive_text` will be empty
- JSON responses will not contain `text` fields
- N8N workflows will need updating to remove OCR text processing

---

## 📝 **EXECUTION ORDER:**
1. Update requirements.txt & Dockerfile
2. Delete ocr_utils.py
3. Clean utils.py
4. Update media_utils.py
5. Update database.py
6. Update tests
7. Update SQL queries
8. Update documentation
9. Rebuild Docker image
10. Test with curl commands 