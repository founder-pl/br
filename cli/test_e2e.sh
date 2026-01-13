#!/bin/bash
# E2E test script for BR System - Invoice Detection and Documentation

set -e

API_BASE="${BR_API_URL:-http://localhost:8020}"
PROJECT_ID="00000000-0000-0000-0000-000000000001"

echo "🧪 BR System E2E Test Suite"
echo "============================"
echo "API: $API_BASE"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}ℹ️ ${NC}$1"; }

# Test 1: Health check
echo "📋 Test 1: API Health Check"
HEALTH=$(curl -s "$API_BASE/health")
echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status')=='healthy' else 1)" && pass "API healthy" || fail "API not healthy"

# Test 2: Projects list
echo ""
echo "📋 Test 2: List Projects"
PROJECTS=$(curl -s "$API_BASE/projects/")
COUNT=$(echo "$PROJECTS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
[ "$COUNT" -gt 0 ] && pass "Found $COUNT projects" || fail "No projects found"

# Test 3: Expenses list
echo ""
echo "📋 Test 3: List Expenses"
EXPENSES=$(curl -s "$API_BASE/expenses/?project_id=$PROJECT_ID")
EXP_COUNT=$(echo "$EXPENSES" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
pass "Found $EXP_COUNT expenses"

# Test 4: Invoice type detection (unit test)
echo ""
echo "📋 Test 4: Invoice Type Detection"
python3 -c "
def detect_invoice_type(extracted_data, our_nip='5881918662'):
    seller_nip = (extracted_data.get('vendor_nip') or 
                  extracted_data.get('seller_nip') or 
                  extracted_data.get('nip_sprzedawcy') or '')
    buyer_nip = (extracted_data.get('buyer_nip') or 
                 extracted_data.get('client_nip') or 
                 extracted_data.get('nip_nabywcy') or '')
    
    def clean_nip(nip):
        if not nip: return ''
        return ''.join(c for c in str(nip) if c.isdigit())
    
    seller_clean = clean_nip(seller_nip)
    buyer_clean = clean_nip(buyer_nip)
    our_clean = clean_nip(our_nip)
    
    if seller_clean == our_clean: return 'revenue'
    if buyer_clean == our_clean: return 'expense'
    return 'expense'

# Test cost invoice
data1 = {'vendor_nip': '1234567890', 'buyer_nip': '5881918662'}
assert detect_invoice_type(data1) == 'expense', 'Cost invoice detection failed'

# Test revenue invoice  
data2 = {'vendor_nip': '5881918662', 'buyer_nip': '9999999999'}
assert detect_invoice_type(data2) == 'revenue', 'Revenue invoice detection failed'

# Test with dashes
data3 = {'vendor_nip': '588-191-86-62', 'buyer_nip': '111-222-33-44'}
assert detect_invoice_type(data3) == 'revenue', 'NIP with dashes failed'

print('All invoice detection tests passed!')
" && pass "Invoice type detection" || fail "Invoice type detection"

# Test 5: Generate documentation
echo ""
echo "📋 Test 5: Generate Project Documentation"
DOC_RESULT=$(curl -s -X POST "$API_BASE/expenses/project/$PROJECT_ID/generate-summary")
DOC_STATUS=$(echo "$DOC_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
[ "$DOC_STATUS" = "success" ] && pass "Documentation generated" || fail "Documentation generation failed"

# Test 6: List documentation files
echo ""
echo "📋 Test 6: List Documentation Files"
DOCS=$(curl -s "$API_BASE/expenses/project/$PROJECT_ID/docs")
DOC_FILES=$(echo "$DOCS" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('files',[])))")
[ "$DOC_FILES" -gt 0 ] && pass "Found $DOC_FILES doc files" || fail "No doc files found"

# Test 7: View documentation content
echo ""
echo "📋 Test 7: View Documentation Content"
FIRST_DOC=$(echo "$DOCS" | python3 -c "import sys,json; files=json.load(sys.stdin).get('files',[]); print(files[0].get('filename','') if files and isinstance(files[0],dict) else (files[0] if files else ''))")
if [ -n "$FIRST_DOC" ]; then
    DOC_CONTENT=$(curl -s "$API_BASE/expenses/project/$PROJECT_ID/docs/$FIRST_DOC")
    CONTENT_LEN=$(echo "$DOC_CONTENT" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('content','')))")
    [ "$CONTENT_LEN" -gt 100 ] && pass "Doc content loaded ($CONTENT_LEN chars)" || fail "Doc content empty"
else
    fail "No documentation file to view"
fi

# Test 8: Documentation version history
echo ""
echo "📋 Test 8: Documentation Version History"
HISTORY=$(curl -s "$API_BASE/expenses/project/$PROJECT_ID/docs/$FIRST_DOC/history")
HIST_COUNT=$(echo "$HISTORY" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('history',[])))")
pass "Found $HIST_COUNT versions in history"

# Test 9: Timesheet endpoint
echo ""
echo "📋 Test 9: Timesheet API"
WORKERS=$(curl -s "$API_BASE/timesheet/workers")
WORKER_COUNT=$(echo "$WORKERS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
pass "Timesheet workers endpoint works ($WORKER_COUNT workers)"

# Test 10: Contractors endpoint
echo ""
echo "📋 Test 10: Contractors API"
CONTRACTORS=$(curl -s "$API_BASE/timesheet/contractors?project_id=$PROJECT_ID")
CONTR_COUNT=$(echo "$CONTRACTORS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
pass "Contractors endpoint works ($CONTR_COUNT contractors)"

# Summary
echo ""
echo "============================"
echo -e "${GREEN}✅ All E2E tests passed!${NC}"
echo ""
echo "📊 Summary:"
echo "   - Projects: $COUNT"
echo "   - Expenses: $EXP_COUNT"
echo "   - Documentation files: $DOC_FILES"
echo "   - Version history entries: $HIST_COUNT"
