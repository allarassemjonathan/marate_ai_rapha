# End-to-End Test for Dynamic Column Management System

## Test Overview
This test verifies that the dynamic column management system works correctly from database to UI.

## Prerequisites
- Flask server running on http://localhost:5000 (or your configured port)
- Administrator access (user: Dr Toralta G .Josephine)
- Empty or test database

## Test Steps

### 1. Initial System Verification
**Goal**: Verify the system starts with default columns

**Steps**:
1. Start the Flask application
2. Navigate to login page
3. Login with administrator credentials
4. Check that you see "Gestion des Colonnes" in navigation
5. Verify main page loads without errors

**Expected Result**: 
- Application loads successfully
- Default patient columns are visible in the table
- Add patient form shows default fields

### 2. Column Management Interface Test
**Goal**: Verify the column management UI works

**Steps**:
1. Click "Gestion des Colonnes" in navigation
2. Verify you see existing columns in the table
3. Check that all default columns are marked as "Visible"
4. Verify essential columns (id, name, created_at) cannot be deleted

**Expected Result**:
- Column management page loads
- All existing columns displayed with correct metadata
- Essential columns show "Essentielle" instead of delete button

### 3. Add New Column Test
**Goal**: Test adding a new custom column

**Steps**:
1. In column management page, fill out "Add New Column" form:
   - Column name: `allergies`
   - Display name: `Allergies`
   - Data type: `Texte`
2. Click "Ajouter Colonne"
3. Verify success message appears
4. Check that new column appears in the table
5. Navigate back to main page
6. Verify new column appears in patient table headers
7. Verify new column appears in add patient form

**Expected Result**:
- Column added successfully
- New column visible in management interface
- New column appears in main interface table and form

### 4. Toggle Column Visibility Test
**Goal**: Test hiding and showing columns

**Steps**:
1. Go to column management page
2. Find a non-essential column (e.g., "adresse")
3. Uncheck the visibility toggle
4. Verify status changes to "Masquée"
5. Navigate to main page
6. Verify column is no longer visible in table headers
7. Verify column is no longer in add patient form
8. Go back to column management
9. Re-enable the column
10. Verify it reappears in main interface

**Expected Result**:
- Column visibility toggles correctly
- Hidden columns don't appear in main interface
- Re-enabled columns reappear immediately

### 5. Patient Data Persistence Test
**Goal**: Verify patient data works with dynamic columns

**Steps**:
1. Add a patient with data in both old and new columns
2. Verify patient appears in the table
3. Add another column and toggle some column visibility
4. Verify existing patient data still displays correctly
5. Edit the patient and verify all data is preserved

**Expected Result**:
- Patients can be added with new column structure
- Existing data persists through column changes
- All CRUD operations work correctly

### 6. Column Removal Test
**Goal**: Test removing custom columns

**Steps**:
1. Go to column management page
2. Find the custom column added in step 3 (`allergies`)
3. Click "Supprimer" button
4. Confirm deletion in popup
5. Verify column disappears from management interface
6. Navigate to main page
7. Verify column no longer appears in interface
8. Try to delete an essential column (should fail)

**Expected Result**:
- Custom columns can be deleted
- Essential columns cannot be deleted
- Deleted columns disappear from all interfaces

### 7. API Endpoints Test
**Goal**: Verify backend API works correctly

**Steps**:
1. Open browser developer tools
2. Navigate to main page and check network tab
3. Verify `/api/columns` endpoint returns correct data
4. Add a column and verify `/api/add_column` works
5. Toggle visibility and verify `/api/toggle_column` works
6. Check that all API responses are valid JSON

**Expected Result**:
- All API endpoints return proper JSON responses
- No console errors in browser
- Network requests complete successfully

### 8. Error Handling Test
**Goal**: Test system handles errors gracefully

**Steps**:
1. Try to add a column with invalid name (e.g., "123invalid")
2. Try to add a column that already exists
3. Try to hide an essential column
4. Verify appropriate error messages appear

**Expected Result**:
- Invalid inputs show proper error messages
- System doesn't crash on invalid operations
- User-friendly error messages displayed

### 9. Data Type Validation Test
**Goal**: Test different column data types work

**Steps**:
1. Add columns with different data types:
   - Text: `notes` → `Notes`
   - Number: `blood_sugar` → `Glycémie` 
   - Date: `last_visit` → `Dernière visite`
   - Boolean: `is_urgent` → `Urgent`
2. Verify each appears with appropriate input type in form
3. Add a patient with data in these fields
4. Verify data saves and displays correctly

**Expected Result**:
- Different data types create appropriate form inputs
- Data validates and saves correctly for each type
- Display formatting works for each data type

### 10. Multi-user Session Test
**Goal**: Test system works with multiple user sessions

**Steps**:
1. Open application in two browser windows
2. Login as administrator in both
3. In window 1: Add a new column
4. In window 2: Refresh page and verify new column appears
5. In window 2: Toggle column visibility
6. In window 1: Refresh and verify changes appear

**Expected Result**:
- Changes made in one session appear in other sessions after refresh
- No conflicts between multiple sessions
- Data consistency maintained

## Success Criteria
✅ All 10 test sections pass without errors
✅ Dynamic columns can be added, hidden, shown, and removed
✅ Patient data works correctly with dynamic schema
✅ No console errors or broken functionality
✅ User interface is responsive and intuitive
✅ API endpoints return proper responses
✅ Error handling works appropriately

## Common Issues to Watch For
- Column data not appearing (RealDictRow handling)
- JavaScript errors preventing dynamic loading
- Database query failures with dynamic columns
- Form fields not generating dynamically
- API endpoint returning wrong data format
- Essential columns being deletable
- Data loss when columns are modified

## Test Environment Cleanup
After testing:
1. Remove any test columns created
2. Reset column visibility to default state
3. Remove any test patient data
4. Verify system returns to clean state

---

**Test Date**: _____________
**Tester**: _____________
**Results**: _____________
**Issues Found**: _____________
